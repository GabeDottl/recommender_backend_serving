echo "Standardizing strings to consistent quote-scheme..."
# unify: https://github.com/myint/unify
find . -name '*.py' | xargs unify --in-place
echo "yapf-ing recursively..."
yapf -rip .
