file_path = 'C:/Users/arnav/OneDrive/Desktop/RobinPass.txt'

with open(file_path, 'r') as file:
    file_contents = file.read()

print(file_contents)