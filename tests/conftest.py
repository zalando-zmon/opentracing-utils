from basictracer import SpanRecorder


class Recorder(SpanRecorder):

    def __init__(self, *args, **kwargs):
        self.spans = []
        return super(Recorder, self).__init__(*args, **kwargs)

    def record_span(self, span):
        self.spans.append(span)

    def reset(self):
        self.spans = []
