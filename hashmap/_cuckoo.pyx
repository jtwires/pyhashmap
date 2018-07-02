"""hash table and filter using cuckoo hashing"""

import xxh
import collections

from cpython cimport (
    mem,
    ref,
)
from libc.string cimport memset


cdef class CuckooHashTable:
    """cuckoo hash table"""

    CYCLES = 500
    __marker = object()

    cdef Py_ssize_t _len
    cdef unsigned long _m, _b
    cdef unsigned long long _rows
    cdef ref.PyObject **_data

    def __init__(self, unsigned long m=1024, unsigned long b=4):
        """initialize new table

        :param long m: the number of buckets to create
        :param long b: the number of entries per bucket

        the table will be resized if necessary, but resizing is costly
        and can be avoided if you know how many entries you expect to
        insert. a good rule of thumb is to aim for 85 - 90% occupancy
        (i.e., 0.85 * N == m * b).

        """
        assert m % 2 == 0
        self._m = m
        self._b = b
        self._len = 0
        self._rows = self._m * self._b * 2
        self._data = NULL
        self._rehash(self._m)

    def __dealloc__(self):
        if self._data != NULL:
            for key in self.iterkeys():
                del self[key]
        mem.PyMem_Free(self._data)
        self._data = NULL

    def __len__(self):
        return self._len

    def __nonzero__(self):
        return self._len > 0

    __hash__ = None

    def __contains__(self, key):
        cdef ref.PyObject *val = self._get(key)
        return val != NULL

    def __eq__(self, other):
        items = (
            other.iteritems()
            if hasattr(other, 'iteritems') else
            other.items()
            if hasattr(other, 'items') else
            None
        )
        if items is None:
            return NotImplemented
        cnt = 0
        for cnt, (key, val) in enumerate(items, 1):
            if self.get(key, self.__marker) != val:
                return False
        return cnt == self._len

    def __ne__(self, other):
        return not (self == other)

    def __iter__(self):
        return self.iterkeys()

    def __getitem__(self, key):
        cdef ref.PyObject *val = self._get(key)
        if val == NULL:
            raise KeyError('{}'.format(key))
        return <object>val

    def __setitem__(self, key, val):
        cdef unsigned long b1, b2
        self._buckets(key, &b1, &b2)

        if not self._upsert(b1, key, val) and not self._upsert(b2, key, val):
            self._displace(b1, b2, key, val)

    def __delitem__(self, key):
        cdef unsigned long b1, b2
        self._buckets(key, &b1, &b2)

        if not self._remove(b1, key) and not self._remove(b2, key):
            raise KeyError('{}'.format(key))

    cpdef get(self, key, default=None):
        cdef ref.PyObject *val = self._get(key)
        return default if val == NULL else <object>val

    cpdef keys(self):
        return list(self.iterkeys())

    cpdef values(self):
        return list(self.itervalues())

    cpdef items(self):
        return list(self.iteritems())

    def iterkeys(self):
        cdef ref.PyObject *key
        cdef unsigned long long idx
        for idx in range(0, self._rows, 2):
            key = self._data[idx]
            if key != NULL:
                yield <object>key

    def itervalues(self):
        cdef ref.PyObject *key
        cdef unsigned long long idx
        for idx in range(0, self._rows, 2):
            key = self._data[idx]
            if key != NULL:
                yield <object>self._data[idx + 1]

    def iteritems(self):
        cdef ref.PyObject *key
        cdef unsigned long long idx
        for idx in range(0, self._rows, 2):
            key = self._data[idx]
            if key != NULL:
                yield <object>key, <object>self._data[idx + 1]

    cpdef pop(self, key, default=__marker):
        try:
            val = self[key]
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            del self[key]
            return val

    cpdef popitem(self):
        try:
            key = next(iter(self))
        except StopIteration:
            raise KeyError
        val = self[key]
        del self[key]
        return key, val

    cpdef clear(self):
        try:
            while True:
                self.popitem()
        except KeyError:
            pass

    cpdef setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
        return default

    def update(self, *args, **kwargs):
        if len(args) > 1:
            raise TypeError(
                'update expected at most 1 argument, got {}'.format(
                    len(args)
                )
            )
        if args:
            other = args[0]
            if isinstance(other, CuckooHashTable):
                for key in other:
                    self[key] = other[key]
            elif hasattr(other, 'iterkeys'):
                for key in other.iterkeys():
                    self[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for key, val in other:
                    self[key] = val
        for key, val in kwargs.items():
            self[key] = val

    cdef void _buckets(self,
                       object key,
                       unsigned long *b1,
                       unsigned long *b2):
        cdef unsigned long long idx, idx1, idx2
        cdef unsigned long m
        m = self._m >> 1
        idx = xxh.hash64(hash(key))
        idx1 = idx & 0xFFFFFFFFULL
        idx2 = idx >> 32
        b1[0] = ((idx1 * m) >> 32)
        b2[0] = ((idx2 * m) >> 32) + m

    cdef void _indices(self,
                       unsigned long bucket,
                       unsigned long long *start,
                       unsigned long long *end):
        cdef unsigned long rows = self._b << 1
        start[0] = bucket * rows
        end[0] = start[0] + rows

    cdef ref.PyObject * _search(self,
                                unsigned long bucket,
                                object tgt):
        cdef unsigned long long idx, start, end
        self._indices(bucket, &start, &end)

        cdef ref.PyObject *key
        for idx in range(start, end, 2):
            key = self._data[idx]
            if key != NULL and <object>key == tgt:
                return self._data[idx + 1]

        return NULL

    cdef ref.PyObject * _get(self, object key):
        cdef unsigned long b1, b2
        cdef ref.PyObject *val
        self._buckets(key, &b1, &b2)
        val = self._search(b1, key)
        if val != NULL:
            return val
        val = self._search(b2, key)
        if val != NULL:
            return val
        return NULL

    cdef void _insert(self,
                      unsigned long long idx,
                      object key, object val):
        self._data[idx] = <ref.PyObject *>key
        self._data[idx + 1] = <ref.PyObject *>val
        ref.Py_XINCREF(self._data[idx])
        ref.Py_XINCREF(self._data[idx + 1])
        self._len += 1

    cdef void _release(self,
                       unsigned long long idx):
        ref.Py_XDECREF(self._data[idx])
        ref.Py_XDECREF(self._data[idx + 1])
        self._data[idx] = NULL
        self._data[idx + 1] = NULL
        self._len -= 1

    cdef bint _upsert(self,
                      unsigned long bucket,
                      object key, object val):
        cdef unsigned long long idx, start, end
        self._indices(bucket, &start, &end)

        cdef ref.PyObject *k
        for idx in range(start, end, 2):
            k = self._data[idx]
            if k != NULL and <object>k == key:
                ref.Py_XDECREF(self._data[idx + 1])
                self._data[idx + 1] = <ref.PyObject *>val
                ref.Py_XINCREF(self._data[idx + 1])
                return True

        for idx in range(start, end, 2):
            k = self._data[idx]
            if k == NULL:
                self._insert(idx, key, val)
                return True

        return False

    cdef bint _remove(self,
                      unsigned long bucket,
                      object key):
        cdef unsigned long long idx, start, end
        self._indices(bucket, &start, &end)

        cdef ref.PyObject *k
        for idx in range(start, end, 2):
            k = self._data[idx]
            if k != NULL and <object>k == key:
                self._release(idx)
                return True
        return False

    cdef void _migrate(self, list path, object key, object val):
        cdef unsigned long long idx, nxt
        idx = path.pop()
        while path:
            nxt = path.pop()
            self._data[idx] = self._data[nxt]
            self._data[idx + 1] = self._data[nxt + 1]
            idx = nxt
        self._insert(idx, key, val)

    cdef void _displace(self,
                        unsigned long b1,
                        unsigned long b2,
                        object key, object val) except *:
        cdef unsigned int cycle, cycles
        cdef unsigned long bucket, tgt
        cdef unsigned long long idx, start, end, b
        cdef ref.PyObject *victim

        paths, visited = collections.deque(), set()
        for bucket in (b1, b2):
            self._indices(bucket, &start, &end)
            for idx in range(start, end, 2):
                paths.append([idx])

        cycles = self.CYCLES
        for cycle in range(cycles):
            if not paths:
                break
            path = paths.popleft()
            idx = path[-1]
            visited.add(idx)
            victim = self._data[idx]
            if victim == NULL:
                self._migrate(path, key, val)
                return
            self._buckets(<object>victim, &b1, &b2)
            b = idx / (self._b << 1)
            bucket = <unsigned long>b
            assert b == bucket
            assert b1 == bucket or b2 == bucket
            tgt = b1 if b1 != bucket else b2
            self._indices(tgt, &start, &end)
            for idx in range(start, end, 2):
                if idx not in visited:
                    paths.append(path + [idx])

        if self._m * 2 < self._m:
            raise MemoryError('cannot extend table')

        self._rehash(self._m * 2)

        self._buckets(key, &b1, &b2)
        if not self._upsert(b1, key, val) and not self._upsert(b2, key, val):
            raise MemoryError('collision persisted after extending table')

    cdef void _rehash(self, unsigned long m) except *:
        cdef ref.PyObject **data = self._data
        cdef unsigned long long rows = self._rows

        self._m = m
        self._rows = self._m * self._b * 2

        cdef unsigned long long length = self._rows * sizeof(ref.PyObject *)
        cdef size_t size = <size_t>length
        if size != length:
            raise MemoryError()

        self._data = <ref.PyObject **>mem.PyMem_Malloc(size)
        if not self._data:
            raise MemoryError()
        memset(self._data, 0, size)

        self._len = 0
        cdef unsigned long long idx
        cdef ref.PyObject *key
        cdef ref.PyObject *val
        if data != NULL:
            for idx in range(0, rows, 2):
                key = data[idx]
                val = data[idx + 1]
                if key != NULL:
                    self[<object>key] = <object>val
                    ref.Py_XDECREF(key)
                    ref.Py_XDECREF(val)
