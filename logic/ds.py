"""
ds.py - the three Data Structures kept from the DSA project.

  HashTable : patient ID -> list of that patient's records   (fast lookup)
  BST       : one tree per analyte, ordered by value          (sorted/min/max)
  MaxHeap   : priority queue of alerts, most severe first     (who to review)

The Discrete Maths part (dm.py) uses these structures as its data source,
and dm.py also explains the hash table as a mathematical FUNCTION.
"""

from logic.dm import RANK


# ---------------------------------------------------------------------------
# HASH TABLE
# ---------------------------------------------------------------------------
class HashTable:
    """
    Hash function: polynomial rolling hash
        h = (h * 31 + ord(ch))  for every character, kept below 2**32
        index = h mod size                      (modular arithmetic)
    Collisions: SEPARATE CHAINING - each bucket is a list of [key, records].
    Resize: when keys/size > 0.75 (load factor) the table grows to 2*size+1
            and every key is re-hashed, so chains stay short.
    Time: insert / search O(1) on average, O(n) if every key collides.
    """

    def __init__(self, size=7):
        self.size = size
        self.buckets = [[] for _ in range(size)]
        self.count = 0                      # number of distinct patients

    def hash(self, key):
        h = 0
        for ch in key:
            h = (h * 31 + ord(ch)) % (2 ** 32)
        return h % self.size

    def insert(self, key, record):
        bucket = self.buckets[self.hash(key)]
        for pair in bucket:                 # walk the chain
            if pair[0] == key:
                pair[1].append(record)      # known patient: add a record
                return
        bucket.append([key, [record]])      # new patient
        self.count += 1
        if self.count / self.size > 0.75:
            self._resize()

    def search(self, key):
        for k, records in self.buckets[self.hash(key)]:
            if k == key:
                return records
        return None

    def keys(self):
        return [k for bucket in self.buckets for k, _ in bucket]

    def all_records(self):
        return [r for bucket in self.buckets for _, recs in bucket for r in recs]

    def _resize(self):
        old = self.buckets
        self.size = self.size * 2 + 1
        self.buckets = [[] for _ in range(self.size)]
        for bucket in old:
            for pair in bucket:
                self.buckets[self.hash(pair[0])].append(pair)


# ---------------------------------------------------------------------------
# BINARY SEARCH TREE
# ---------------------------------------------------------------------------
class Node:
    def __init__(self, record):
        self.record = record
        self.left = None
        self.right = None


class BST:
    """
    Rule: left subtree < node <= right subtree (equal values go right).
    insert / search: start at the root, go left if smaller, else right.
    min = leftmost node, max = rightmost node.
    Inorder (left, node, right) gives values in ascending order.
    Time: O(log n) average, O(n) if the tree becomes a chain.
    Loops are used instead of recursion so a long chain is still safe.
    """

    def __init__(self):
        self.root = None

    def insert(self, record):
        new = Node(record)
        if self.root is None:
            self.root = new
            return
        cur = self.root
        while True:
            if record["value"] < cur.record["value"]:
                if cur.left is None:
                    cur.left = new
                    return
                cur = cur.left
            else:
                if cur.right is None:
                    cur.right = new
                    return
                cur = cur.right

    def minimum(self):
        cur = self.root
        while cur and cur.left:
            cur = cur.left
        return cur.record if cur else None

    def maximum(self):
        cur = self.root
        while cur and cur.right:
            cur = cur.right
        return cur.record if cur else None

    def inorder(self):
        """Iterative inorder traversal using an explicit STACK (LIFO)."""
        out, stack, cur = [], [], self.root
        while stack or cur:
            while cur:                      # go as far left as possible
                stack.append(cur)
                cur = cur.left
            cur = stack.pop()               # visit the node
            out.append(cur.record)
            cur = cur.right                 # then its right subtree
        return out


# ---------------------------------------------------------------------------
# PRIORITY QUEUE (binary max-heap)
# ---------------------------------------------------------------------------
class MaxHeap:
    """
    The heap is a list. For index i: children 2i+1 and 2i+2, parent (i-1)//2.
    push: append, then SIFT UP while the item beats its parent.
    pop : take the root, move the last item to the root, SIFT DOWN.
    Priority: higher severity first; same severity -> earlier arrival first.
    Time: push O(log n), pop O(log n).
    """

    def __init__(self):
        self.heap = []

    def __len__(self):
        return len(self.heap)

    @staticmethod
    def _before(a, b):
        if RANK[a["severity"]] != RANK[b["severity"]]:
            return RANK[a["severity"]] > RANK[b["severity"]]
        return a["seq"] < b["seq"]

    def push(self, item):
        h = self.heap
        h.append(item)
        i = len(h) - 1
        while i > 0:                                    # sift up
            parent = (i - 1) // 2
            if not self._before(h[i], h[parent]):
                break
            h[i], h[parent] = h[parent], h[i]
            i = parent

    def pop(self):
        h = self.heap
        if not h:
            return None
        top, last = h[0], h.pop()
        if h:
            h[0] = last
            i, n = 0, len(h)
            while True:                                 # sift down
                l, r, best = 2 * i + 1, 2 * i + 2, i
                if l < n and self._before(h[l], h[best]):
                    best = l
                if r < n and self._before(h[r], h[best]):
                    best = r
                if best == i:
                    break
                h[i], h[best] = h[best], h[i]
                i = best
        return top

    def ordered(self):
        """Serving order without changing the real heap (pop from a copy)."""
        copy = MaxHeap()
        copy.heap = self.heap[:]
        return [copy.pop() for _ in range(len(copy))]
