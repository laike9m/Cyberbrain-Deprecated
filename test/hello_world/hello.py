import cyberbrain


def main():
    print("hello world")
    cyberbrain.register(None, output_path="test/hello_world")


if __name__ == "__main__":
    cyberbrain.init()
    main()
