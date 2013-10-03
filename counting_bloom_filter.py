#!/usr/bin/env python

import array
import struct
import math
import mmh3


class CountingBloomFilter(object):
    def __init__(self, capacity, error=0.005, dtype="B"):
        self.capacity = capacity
        self.error = error
        self.num_bytes = int(-capacity * math.log(error) / math.log(2)**2) + 1
        self.num_hashes = int(self.num_bytes / capacity * math.log(2)) + 1
        self.dtype = dtype
        self.data = array.array(dtype, (0,) * self.num_bytes) 

    def _indexes(self, key):
        """
        Generates the indicies corresponding to the given key
        """
        for i in xrange(self.num_hashes):
            h1, h2 = mmh3.hash64(key)
            yield (h1 + i * h2) % self.num_bytes

    def add(self, key, N=1):
        """
        Adds `N` counts to the indicies given by the key
        """
        assert isinstance(key, str)
        for index in self._indexes(key):
            self.data[index] += N
        return self

    def remove(self, key, N=1):
        """
        Removes `N` counts to the indicies given by the key
        """
        assert isinstance(key, str)
        indexes = list(self._indexes(key))
        if not any(self.data[index] < N for index in indexes):
            for index in indexes:
                self.data[index] -= N
        return self

    def remove_all(self, N=1):
        """
        Removes `N` counts to all indicies.  Useful for expirations
        """
        for i in xrange(self.num_bytes):
            if self.data[i] >= N:
                self.data[i] -= N

    def contains(self, key):
        """
        Check if the current bloom contains the key `key`
        """
        assert isinstance(key, str)
        return all(self.data[index] != 0 for index in self._indexes(key))

    def tofile(self, f):
        """
        Writes the bloom into the given fileobject.
        """
        header = struct.pack("QdQQc", self.capacity, self.error, self.num_bytes, self.num_hashes, self.dtype)
        f.write(header + "\n")
        self.data.tofile(f)

    @classmethod
    def fromfile(cls, f):
        """
        Reads the bloom from the given fileobject and returns the python object
        """
        self = cls.__new__(cls)
        header = f.readline()[:-1]
        self.capacity, self.error, self.num_bytes, self.num_hashes, self.dtype = struct.unpack("QdQQc", header)
        self.data = array.array(self.dtype)
        self.data.fromfile(f, self.num_bytes)
        return self

    def __contains__(self, key):
        return self.contains(key)

    def __add__(self, other):
        return self.add(other)

    def __sub__(self, other):
        return self.remove(other)


