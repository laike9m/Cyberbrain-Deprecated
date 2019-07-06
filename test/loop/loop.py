# Program that contains loops

import cyberbrain

cyberbrain.init()

for i in range(3):
    print(i)
else:
    print("in else")

while i > 0:
    i -= 1
    if i == 1:
        break

cyberbrain.register(i)
