import unittest

from hashmap import cuckoo

class MutableHashTable(object):

    class TestCases(unittest.TestCase):

        def construct(self, **kwargs):
            raise NotImplementedError()

        def test_insert(self):
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

        def test_insert_many(self):
            d, cnt = self.construct(), 1 << 15
            for i in xrange(cnt):
                d[i] = i
            self.assertEqual(len(d), cnt)
            for i in xrange(cnt):
                self.assertEqual(d[i], i)

        def test_remove(self):
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
            d = self.construct()
            for i in xrange(10):
                d[str(i)] = i
            self.assertEqual(
                list(sorted(d)),
                [str(i) for i in xrange(10)]
            )
            self.assertEqual(
                list(sorted(d.items())),
                [(str(i), i) for i in xrange(10)]
            )


class CuckooTestCases(MutableHashTable.TestCases):

    def construct(self, **kwargs):
        return cuckoo.HashTable(**kwargs)
