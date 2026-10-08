import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as Item

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import sentence_chunks


class SentenceTests(unittest.TestCase):
    def test_punctuation_and_pause(self):
        words = [Item(start=0, end=.4, word=' Hello.'),
                 Item(start=.5, end=1, word=' I'),
                 Item(start=1, end=1.5, word=' practise'),
                 Item(start=2.5, end=3, word=' daily.')]
        result = sentence_chunks([Item(words=words)])
        self.assertEqual([s['text'] for s in result], ['Hello.', 'I practise', 'daily.'])
        self.assertEqual(result[1]['start'], .5)
        self.assertEqual(result[1]['end'], 1.5)

    def test_sentence_across_segments(self):
        result = sentence_chunks([Item(words=[Item(start=0,end=1,word=' Good')]),
                                  Item(words=[Item(start=1,end=2,word=' morning!')])])
        self.assertEqual(result, [{'start':0,'end':2,'text':'Good morning!'}])

    def test_empty(self):
        self.assertEqual(sentence_chunks([Item(words=None)]), [])


if __name__ == '__main__':
    unittest.main()
