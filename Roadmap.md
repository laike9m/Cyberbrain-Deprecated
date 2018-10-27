As the first step, we should build a prototype that is as simple as possible to test if the idea works. No import statement, no class, no fancy stuff, just global variables and functions.

```python
def foo(input_var: int):
    return input_var + 1

def bar(input_var: int):
    return input_var - 1

def main():
    a = 1
    b = foo(a)
    c = bar(b)

if __name__ == `__main__`:
    main()
```

Supposed we want to analyze `c`, expected output is something like:

```
a(value: 1)
-> foo(a)
-> b(value: 2, procedure: b = a + 1)
-> bar(b)
-> c(value: 1, procedure: c = b - 1)
```
