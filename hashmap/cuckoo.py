"""hash table and probabilistic filter using cuckoo hashing"""

import collections

import xxhash


class PyCuckooHashTable(collections.MutableMapping):
    """pure python cuckoo hash table implementation"""

    _nil = object()
    CYCLES = 500

    def __init__(self, m=1024, b=4):  # pylint: disable=super-init-not-called
        """initialize new table

        :param long m: the number of buckets to create
        :param long b: the number of entries per bucket

        the table will be resized if necessary, but resizing is costly
        and can be avoided if you know how many entries you expect to
        insert. a good rule of thumb is to aim for 85 - 90% occupancy
        (i.e., 0.85 * N == m * b).

        """
        assert m % 2 == 0
        self._b = b
        self._m = m
        self._len = 0
        self._data = [self._nil] * self._m * self._b * 2

    def __len__(self):
        return self._len

    def __nonzero__(self):
        return self._len > 0

    def __iter__(self):
        data = self._data
        for idx in xrange(0, len(self._data), 2):
            key = data[idx]
            if key is not self._nil:
                yield key

    def __getitem__(self, key):
        b1, b2 = self._buckets(key)
        val = self._search(b1, key)
        if val is not self._nil:
            return val
        val = self._search(b2, key)
        if val is not self._nil:
            return val
        raise KeyError('{}'.format(key))

    def __setitem__(self, key, val):
        b1, b2 = self._buckets(key)
        if not self._upsert(b1, key, val) and not self._upsert(b2, key, val):
            self._displace(b1, b2, key, val)

    def __delitem__(self, key):
        b1, b2 = self._buckets(key)
        if not self._remove(b1, key) and not self._remove(b2, key):
            raise KeyError('{}'.format(key))

    def _buckets(self, key):
        idx = xxhash.xxh64(str(hash(key))).intdigest()
        # see https://lemire.me/blog/2016/06/27/
        # a-fast-alternative-to-the-modulo-reduction/
        idx1, idx2, m = idx & 0xFFFFFFFF, idx >> 32, self._m / 2
        return (
            ((idx1 * m) >> 32),
            ((idx2 * m) >> 32) + m,
        )

    def _indices(self, bucket):
        idx = bucket * self._b * 2
        return xrange(idx, idx + self._b * 2, 2)

    def _search(self, bucket, key):
        data = self._data
        for idx in self._indices(bucket):
            if data[idx] == key:
                return data[idx + 1]
        return self._nil

    def _upsert(self, bucket, key, val):
        data = self._data
        for idx in self._indices(bucket):
            if data[idx] == key:
                data[idx + 1] = val
                return True
        for idx in self._indices(bucket):
            if data[idx] is self._nil:
                data[idx] = key
                data[idx + 1] = val
                self._len += 1
                return True
        return False

    def _remove(self, bucket, key):
        data = self._data
        for idx in self._indices(bucket):
            if data[idx] == key:
                data[idx] = self._nil
                data[idx + 1] = self._nil
                self._len -= 1
                return True
        return False

    def _rehash(self):
        self._m *= 2
        data = self._data
        self._data = [self._nil] * self._m * self._b * 2

        self._len = 0
        for idx in xrange(0, len(data), 2):
            if data[idx] is not self._nil:
                self[data[idx]] = data[idx + 1]

    def _displace(self, b1, b2, key, val):
        data = self._data

        def _migrate(path):
            idx = path.pop()
            while path:
                nxt = path.pop()
                data[idx] = data[nxt]
                data[idx + 1] = data[nxt + 1]
                idx = nxt
            data[idx] = key
            data[idx + 1] = val
            self._len += 1

        # breadth-first search for a non-full bucket
        paths = collections.deque(
            [
                [idx]
                for bucket in (b1, b2)
                for idx in self._indices(bucket)
            ]
        )
        for _ in xrange(self.CYCLES):
            path = paths.popleft()
            idx = path[-1]
            victim = data[idx]
            if victim is self._nil:
                _migrate(path)
                return
            b1, b2 = self._buckets(victim)
            bucket = idx / (self._b * 2)
            assert b1 == bucket or b2 == bucket
            tgt = b1 if b1 != bucket else b2
            paths.extend(
                [
                    path + [nxt]
                    for nxt in self._indices(tgt)
                ]
            )

        self._rehash()
        self[key] = val


try:
    # pylint: disable=unused-import
    from hashmap._cuckoo import CuckooHashTable as HashTable
except ImportError:
    HashTable = PyCuckooHashTable
