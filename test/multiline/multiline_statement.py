"""Program that has multiline statements."""


import cyberbrain

cyberbrain.init()  # Can we use import hook to achieve this?


y = {
    "longlonglonglonglonglonglonglong": 1,
    "longlonglonglonglonglonglonglonglong": 2,
    "longlonglonglonglonglonglonglonglonglong": 3,
}


def f(**kwargs):
    pass


x = f(
    longlonglonglonglonglonglonglong=1,
    longlonglonglonglonglonglonglonglong=2,
    longlonglonglonglonglonglonglonglonglong=3,
)

cyberbrain.register(y)  # register has to be called after init
