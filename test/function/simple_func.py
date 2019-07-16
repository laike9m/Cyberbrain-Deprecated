"""Program with (nested) function calls."""

import cyberbrain


def main():
    def f(x, y):
        return x + y

    x = 1
    y = f(x, f(1, 1))  # y is our target. TODO: add [1 for x in range(4)] as arg.
    cyberbrain.register()  # register has to be called after init


if __name__ == "__main__":
    cyberbrain.init()  # Can we use import hook to achieve this?
    main()
