from consensus import Node, packageTx

import json
import time

from os import urandom
from random import sample, shuffle
from binascii import hexlify


def test_random():
	resources = [hexlify(urandom(16)) for _ in range(300)]
	transactions = [(hexlify(urandom(16)), sample(resources,2), []) for _ in range(300)]

	n = Node(resources, 2)
	shuffle(transactions)
	tx_list = sample(transactions, 100)
	for tx in transactions:
		n.process(tx)

	n2 = Node(resources,2)
	n.gossip_towards(n2)
	for tx in transactions:
		n2.process(tx)

class Timer:    
    def __enter__(self):
        self.start = time.clock()
        return self

    def __exit__(self, *args):
        self.end = time.clock()
        self.interval = self.end - self.start

def test_wellformed():
	resources = [hexlify(urandom(16)) for _ in range(1000)]
	# def packageTx(data, deps, num_out)
	transactions = []
	for x in range(100):
		deps = sample(resources,2)
		data = json.dumps({"ID":x})
		tx = packageTx(data, deps, 2)
		transactions.append((tx, data))
	# [(hexlify(urandom(16)), sample(resources,2), []) for x in range(300)]

	n = Node(resources, 1)
	n.quiet = True
	shuffle(transactions)
	# tx_list = sample(transactions, 100)

	with Timer() as t:
		for tx, data in transactions:
			idx, deps, out = tx

			## First perform the Tx checks
			assert packageTx(data, deps, 2) == tx

			## Now process this transaction
			n.process(tx)
			
	print "Time taken: %2.2f sec" % (t.interval) 

def test_small():
	T1 = ("T1", ["A", "B"], [])
	T2 = ("T2", ["B", "C"], [])

	n = Node(["A", "B", "C"],1)
	n.process(T1)
	n.process(T2)
	assert "T1" in n.commit_yes
	assert "T2" not in n.commit_yes

def test_small_chain():
	T1 = ("T1", ["A"], ["B"])
	T2 = ("T2", ["B"], ["C"])

	n = Node(["A"],1)
	n.process(T1)
	n.process(T2)
	assert "C" in n.pending_available

def test_chain_conflict():
	T1 = ("T1", ["A"], ["B"])
	T2 = ("T2", ["A"], ["C"])
	T3 = ("T3", ["B"], ["D"])
	T4 = ("T4", ["C"], ["F"])

	n = Node(["A"],1)
	for tx in [T1, T2, T3, T4]:
		n.process(tx)

def test_quorum_simple():
	T1 = ("T1", ["A", "B"], [])
	T2 = ("T2", ["B", "C"], [])

	n1 = Node(["A", "B", "C"], 2)
	n2 = Node(["A", "B", "C"], 2)
	n3 = Node(["A", "B", "C"], 2)

	n1.process(T1)
	n2.process(T2)
	n2.process(T1)
	n3.process(T1)

	n1.gossip_towards(n2)
	n3.gossip_towards(n2)

	n2.process(T1)
	assert "T1" in n2.commit_yes

def test_shard_simple():
	T1 = ("333", ["444", "ccc"], [])
	T2 = ("bbb", ["444", "ddd"], [])

	n1 = Node(["444"], 1, name="n1", shard=["000", "aaa"])
	n2 = Node(["ccc", "ddd"], 1, name="n2", shard=["aaa", "fff"])

	n1.process(T1)
	n1.process(T2)
	print n1.pending_vote
	n2.process(T2)
	n2.process(T1)

	n1.gossip_towards(n2)

	n2.process(T1)
	n2.process(T2)
	
	assert '333' in n2.commit_yes

def test_shard_many():
	limits = sorted([hexlify(urandom(32)) for _ in range(100)])
	limits = ["0" * 64] + limits + ["f" * 64]

	pre = ["444", "ccc", "ddd"]
	nodes = [Node(pre, 1, name="n%s" % i, shard=[b0,b1]) for i, (b0, b1) in enumerate(zip(limits[:-1],limits[1:]))]

	T1 = ("333", ["444", "ccc"], [])
	T2 = ("bbb", ["444", "ddd"], [])

	n1 = [n for n in nodes if n._within_TX(T1)]
	n2 = [n for n in nodes if n._within_TX(T2)]

	assert len(n1) == 3 and len(n2) == 3

	for n in n1:
		n.process(T1)

	for n in n2:
		n.process(T2)		

