class Segment:
    def __init__(self, start, stop):
        self.start = start
        self.stop = stop

    def length(self):
        return self.stop - self.start

    def __repr__(self):
        return "Segment([{}, {}])".format(self.start, self.stop)

def intersect_ranges(xs, ys):
    # Try to get the first range in each iterator:
    try:
        x, y = next(xs), next(ys)
    except StopIteration:
        return

    while True:
        # Yield the intersection of the two ranges, if it's not empty:
        intersection = Segment(
            max(x.start, y.start),
            min(x.stop, y.stop)
        )
        if intersection.length() > 0:
            yield intersection

        # Try to increment the range with the earlier stopping value:
        try:
            if x.stop <= y.stop:
                x = next(xs)
            else:
                y = next(ys)
        except StopIteration:
            return

def is_boolean(x):
    return x == 'NA' or int(x) in [0,1]