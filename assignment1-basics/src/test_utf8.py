test_str = "hello! こんにちは!"
utf8_encoded = test_str.encode('utf-8')
utf32_encoded = test_str.encode('utf-32')
print(f"utf8_encoded: {utf8_encoded}")
print(f"utf32_encoded: {utf32_encoded}")

# Print the type of the encoded strings
print(type(utf8_encoded))

# Get the byte values for the encoded string (integers from 0 to 255)
byte_values = list(utf8_encoded)
print("Byte values in UTF-8 encoding:")
print(byte_values)

# One byte does not necessarily represent one character in UTF-8
# For example, the character 'こ' is represented by three bytes in UTF-8
print(f"len(test_str): {len(test_str)}")  # Length of the original string
print(f"len(utf8_encoded): {len(utf8_encoded)}")  # Length of the encoded byte string
print(f"len(utf32_encoded): {len(utf32_encoded)}")  # Length of the UTF-32 encoded byte string
print(f"utf8_encoded.decode('utf-8'): {utf8_encoded.decode('utf-8')}")  # Decoding back to string