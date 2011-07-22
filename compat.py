import itertools

try:
  itertools.count(1, 1)
except TypeError:
  def _count(start=0, step=1):
    n = start
    while True:
      yield n
      n += step
  itertools.count = _count
