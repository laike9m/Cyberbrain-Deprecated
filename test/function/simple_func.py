"""Program with (nested) function calls."""

import cyberbrain


def main():
    def f(x, y):
        return x + y

    x = 1
    y = f(x, f(1, 1))
    cyberbrain.register(y)


if __name__ == "__main__":
    cyberbrain.init()
    main()
