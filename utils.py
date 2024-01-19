import typing

def read_file(filename: str) -> bytes | None:
	try:
		f = open(filename, "rb")
		t = f.read()
		f.close()
		return t
	except FileNotFoundError:
		return

def write_file(filename: str, content: bytes):
	f = open(filename, "wb")
	f.write(content)
	f.close()

T = typing.TypeVar('T')
def optional(optional: T | None, default: T) -> T:
	if optional == None: return default
	return optional