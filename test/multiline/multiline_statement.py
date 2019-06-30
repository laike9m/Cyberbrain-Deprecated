import cyberbrain


def main():
    y = {
        "longlonglonglong": 1,
        "longlonglonglonglong": 2,
        "longlonglonglonglonglong": 3,
    }
    cyberbrain.register()  # register has to be called after init


if __name__ == "__main__":
    cyberbrain.init()  # Can we use import hook to achieve this?
    main()
