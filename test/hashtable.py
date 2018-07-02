"""hash table unit tests"""

import unittest

from hashmap import (
    cuckoo,
    _cuckoo,
)


class MutableHashTable(object):  # pylint: disable=too-few-public-methods
    """hashtable test wrapper"""

    class TestCases(unittest.TestCase):
        """hashtable test cases"""

        def construct(self, **kwargs):
            """create a new hash table"""
            raise NotImplementedError()

        def test_insert(self):
            """hashtable insertion"""
            d = self.construct()
            self.assertFalse(d)
            self.assertEqual(len(d), 0)

            d[1] = 1
            self.assertTrue(d)
            self.assertEqual(len(d), 1)
            self.assertIn(1, d)
            self.assertEqual(d[1], 1)

            d[1] = 2
            self.assertEqual(len(d), 1)
            self.assertEqual(d[1], 2)

            with self.assertRaises(KeyError):
                self.assertEqual(d[2], 2)

        def test_pop(self):
            """hashtable default remove"""
            d = self.construct()
            with self.assertRaises(KeyError):
                d.pop(1)
            o = object()
            self.assertEqual(d.pop(1, o), o)
            d[1] = 1
            d.pop(1)

        def test_insert_many(self):
            """hashtable resize"""
            d, cnt = self.construct(), 1 << 15
            for i in xrange(cnt):
                d[i] = i
            self.assertEqual(len(d), cnt)
            for i in xrange(cnt):
                self.assertEqual(d[i], i)

        def test_remove(self):
            """hashtable remove"""
            d = self.construct()
            for i in xrange(10):
                d[i] = i
            for i in xrange(10):
                self.assertEqual(d[i], i)
            self.assertEqual(len(d), 10)
            self.assertEqual(len(list(d)), 10)

            del d[0]
            self.assertNotIn(0, d)
            self.assertEqual(len(d), 9)
            self.assertEqual(len(list(d)), 9)
            with self.assertRaises(KeyError):
                del d[0]

            d[0] = 1
            self.assertEqual(d[0], 1)
            self.assertEqual(len(d), 10)
            self.assertEqual(len(list(d)), 10)

            size = 10
            while d:
                size -= 1
                d.popitem()
                self.assertEqual(len(d), size)
                self.assertEqual(len(list(d)), size)
            self.assertFalse(d)

        def test_iterate(self):
            """hashtable iterators"""
            d = self.construct()
            for i in xrange(10):
                d[str(i)] = i
            self.assertEqual(
                list(sorted(d)),
                [str(i) for i in xrange(10)]
            )
            self.assertEqual(
                list(sorted(d.keys())),
                [str(i) for i in xrange(10)]
            )
            self.assertEqual(
                list(sorted(d.iterkeys())),
                [str(i) for i in xrange(10)]
            )
            self.assertEqual(
                list(sorted(d.values())),
                list(xrange(10)),
            )
            self.assertEqual(
                list(sorted(d.itervalues())),
                list(xrange(10)),
            )
            self.assertEqual(
                list(sorted(d.items())),
                [(str(i), i) for i in xrange(10)]
            )
            self.assertEqual(
                list(sorted(d.iteritems())),
                [(str(i), i) for i in xrange(10)]
            )

        def test_hash_operator(self):
            """hashtable respects custom hashes"""
            class Value(object):  # pylint: disable=too-few-public-methods
                """class with custom hash method"""

                def __init__(self, val):
                    self.val = val

                def __hash__(self):
                    return hash(self.val)

            v1, v2 = Value(1), Value(1)
            self.assertNotEqual(v1, v2)
            self.assertEqual(hash(v1), hash(v2))

            d = self.construct()
            d[v1] = True
            self.assertNotIn(v2, d)

        def test_equality_operator(self):
            """hashtable respects custom equality operators"""
            class Value(object):  # pylint: disable=too-few-public-methods
                """class with custom equality method"""

                def __init__(self, val):
                    self.val = val

                def __hash__(self):
                    return hash(self.val)

                def __eq__(self, other):
                    if not isinstance(other, Value):
                        return NotImplemented
                    return self.val == other.val

            v1, v2 = Value(1), Value(1)
            self.assertEqual(v1, v2)
            self.assertEqual(hash(v1), hash(v2))

            d = self.construct()
            d[v1] = True
            self.assertIn(v2, d)

        def test_dict_equality(self):
            """hashtable equality operator"""
            d1, d2 = self.construct(), self.construct()
            self.assertEqual(d1, d2)
            self.assertNotEqual(d1, object())
            d1[1] = True
            self.assertNotEqual(d1, d2)
            self.assertNotEqual(d2, d1)
            d2[1] = True
            self.assertEqual(d1, d2)
            self.assertEqual(d2, d1)

        def test_update(self):
            """hashtable update method"""
            d = self.construct()
            d.update([('foo', 'bar')])
            self.assertEqual(
                d,
                {
                    'foo': 'bar'
                }
            )
            d.update({'baz': 'bazzle'})
            self.assertEqual(
                d,
                {
                    'foo': 'bar',
                    'baz': 'bazzle',
                }
            )
            d.update({'foo': 'barnone'})
            self.assertEqual(
                d,
                {
                    'foo': 'barnone',
                    'baz': 'bazzle',
                }
            )


class DictTestCases(MutableHashTable.TestCases):
    """builtin dictionary test cases"""

    def construct(self, **kwargs):
        return dict()


class PyCuckooTestCases(MutableHashTable.TestCases):
    """python cuckoo hash test cases"""

    def construct(self, **kwargs):
        return cuckoo.PyCuckooHashTable(**kwargs)


class CyCuckooTestCases(MutableHashTable.TestCases):
    """cython cuckoo hash test cases"""

    def construct(self, **kwargs):
        return _cuckoo.CuckooHashTable(**kwargs)
