from argparse import ArgumentParser
parser = ArgumentParser()

def parse_known_args():
  args, _ = parser.parse_known_args()
  return args

