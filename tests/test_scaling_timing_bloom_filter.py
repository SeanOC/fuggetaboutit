#!/usr/bin/env python

from scaling_timing_bloom_filter import ScalingTimingBloomFilter
import tornado.ioloop
import tornado.testing
import time
from utils import TimingBlock

class TestScalingTimingBloomFilter(tornado.testing.AsyncTestCase):
    def test_decay(self):
        stbf = ScalingTimingBloomFilter(500, decay_time=4, ioloop=self.io_loop).start()
        stbf += "hello"
        assert stbf.contains("hello") == True
        try:
            self.wait(timeout = 4)
        except:
            pass
        assert stbf.contains("hello") == False

    def test_holistic(self):
        n = int(1e5)
        N = int(2e5)
        T = 15
        print "ScalingTimingBloom with capacity %e and expiration time %ds" % (n, T)

        with TimingBlock("Initialization"):
            stbf = ScalingTimingBloomFilter(n, decay_time=T, dtype="B", ioloop=self.io_loop)

        orig_decay = stbf.decay
        def new_decay(*args, **kwargs):
            with TimingBlock("Decaying"):
                val = orig_decay(*args, **kwargs)
            return val
        setattr(stbf, "decay", new_decay)
        stbf._setup_decay()
        stbf.start()

        print "State of blooms: %d blooms with expected error %.2f%%" % (len(stbf.blooms), stbf.expected_error()*100.)

        with TimingBlock("Adding %d values" % N, N):
            for i in xrange(N):
                stbf.add(str(i))
        last_insert = time.time()

        print "State of blooms: %d blooms with expected error %.2f%%" % (len(stbf.blooms), stbf.expected_error()*100.)

        with TimingBlock("Testing %d positive values" % N, N):
            for i in xrange(N):
                assert str(i) in stbf

        with TimingBlock("Testing %d negative values" % N, N):
            err = 0
            for i in xrange(N, 2*N):
                if str(i) in stbf:
                    err += 1
            tot_err = err / float(N)
            assert tot_err <= stbf.error, "Error is too high: %f > %f" % (tot_err, stbf.error)

        try:
            t = T - (time.time() - last_insert)
            if t > 0:
                self.wait(timeout = t)
        except:
            pass

        print "State of blooms: %d blooms with expected error %.2f%%" % (len(stbf.blooms), stbf.expected_error()*100.)

        with TimingBlock("Testing %d expired values" % N, N):
            err = 0
            for i in xrange(N):
                if str(i) in stbf:
                    err += 1
            tot_err = err / float(N)
            assert tot_err <= stbf.error, "Error is too high: %f > %f" % (tot_err, stbf.error)

        assert len(stbf.blooms) == 1, "Decay should have pruned all but one bloom filters"
