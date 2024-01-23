import utils
import json
import math
import typing
import base64

def handlebars(data: str, page: "Page") -> str:
	r = ""
	charno = 0
	while charno < len(data):
		char = data[charno]
		if data[charno:charno + len("{{field ")] == "{{field ":
			charno += len("{{field ")
			name = ""
			while data[charno] != " ":
				name += data[charno]
				charno += 1
			charno += 1
			defaultval = ""
			while data[charno:charno + 2] != "}}":
				defaultval += data[charno]
				charno += 1
			charno += 1
			# Substitute the data
			if name in page.data.keys():
				r += page.data[name].decode("UTF-8")
			else:
				r += defaultval.replace("$pagename", page.name)
		elif data[charno:charno + len("{{field64 ")] == "{{field64 ":
			charno += len("{{field64 ")
			name = ""
			while data[charno] != " ":
				name += data[charno]
				charno += 1
			charno += 1
			defaultval = ""
			while data[charno:charno + 2] != "}}":
				defaultval += data[charno]
				charno += 1
			charno += 1
			# Substitute the data
			if name in page.data.keys():
				r += base64.b64encode(page.data[name]).decode("UTF-8")
			else:
				r += base64.b64encode(defaultval.replace("$pagename", page.name).encode("UTF-8")).decode("UTF-8")
		elif data[charno:charno + len("{{pagens}}")] == "{{pagens}}":
			charno += len("{{pagens}}") - 1
			r += page.ns.name
		elif data[charno:charno + len("{{pagename}}")] == "{{pagename}}":
			charno += len("{{pagename}}") - 1
			r += page.name
		else:
			r += char
		charno += 1
	return r

class Buffer:
	def __init__(self, data: bytes):
		self.data = data
		self.pos = 0
	def read(self, n: int) -> bytes:
		result = self.data[self.pos:self.pos + n]
		self.pos += n
		return result
	def readInt(self) -> int:
		result = self.data[self.pos]
		self.pos += 1
		return result
	def canRead(self) -> bool:
		return self.pos < len(self.data) - 1

class NSFileEntry(typing.TypedDict):
	type: str
	content: str
class Namespace:
	def __init__(self, name: str, fields: dict[str, typing.Literal["text", "file"]], defaultPage: str, content: str, files: dict[str, NSFileEntry]):
		self.name = name
		self.fields = fields
		self.defaultPage = defaultPage
		self.content = content
		self.files = files
	@staticmethod
	def fromFile(name: str) -> "Namespace | None":
		raw = utils.read_file(f"pages/{name}/ns.json")
		if raw == None: return
		data = json.loads(raw)
		return Namespace(name, data["fields"], data["defaultPage"], data["content"], data["files"])
	def getContent(self, page: "Page"):
		return handlebars(self.content, page)

class PageHistory:
	def __init__(self, ns: Namespace, name: str, data: "list[tuple[str, Page]]"):
		self.ns = ns
		self.name = name
		self.data: "list[tuple[str, Page]]" = data
	def toBytes(self) -> bytes:
		r: list[int] = []
		for i in self.data:
			# Write message length
			r.append(len(i[0]))
			# Write message
			r.extend([*i[0].encode("UTF-8")])
			# Write page
			r.extend(i[1].toInts())
		return bytes(r)
	def save(self):
		data = self.toBytes()
		filename = f"pages/{self.ns.name}/{self.name}.dat"
		utils.write_file(filename, data)
	@staticmethod
	def fromFile(name: str) -> "PageHistory | None":
		ns = name.split(":")[0]
		pn = name.split(":")[1]
		nso = Namespace.fromFile(ns)
		if nso == None: return
		raw_data = utils.read_file(f"pages/{ns}/{pn}.dat")
		if raw_data == None: return PageHistory(nso, pn, [])
		raw = Buffer(raw_data)
		out: list[tuple[str, Page]] = []
		while raw.canRead():
			out.append(PageHistory.readOneEntry(nso, pn, raw))
		return PageHistory(nso, pn, out)
	@staticmethod
	def readOneEntry(ns: Namespace, name: str, b: Buffer) -> "tuple[str, Page]":
		# Read length of message
		ml = b.readInt()
		# Read message
		message = b.read(ml).decode("UTF-8")
		# print("read message length", ml, "data:", message)
		# Read page
		page = Page.read(ns, name, b)
		# Return
		return (message, page)
	def mostRecent(self):
		if len(self.data) == 0:
			return Page(self.ns, self.name, {})
		return self.data[-1][1]
	def append(self, message: str, data: dict[str, bytes]):
		self.data.append((message, Page(self.ns, self.name, data)))
	def appendEdit(self, message: str, editName: str, editValue: bytes):
		oldPage = self.mostRecent()
		newData = oldPage.data.copy()
		newData[editName] = editValue
		self.append(message, newData)
	def appendDelete(self, message: str):
		self.append(message, {})

class Page:
	def __init__(self, ns: Namespace, name: str, data: dict[str, bytes]):
		self.ns = ns
		self.name = name
		self.data = data
	def getContent(self):
		return self.ns.getContent(self)
	def toInts(self) -> list[int]:
		names = [*self.data.keys()]
		r: list[int] = [len(names)]
		for name in names:
			# Write name length
			r.append(len(name))
			# Write name
			r.extend([*name.encode("UTF-8")])
			# Write value length
			value = self.data[name]
			r.append(math.floor(len(value) / (256 * 256)) % 256)
			r.append(math.floor(len(value) / 256) % 256)
			r.append(len(value) % 256)
			# Write value
			r.extend([*value])
		return r
	@staticmethod
	def read(ns: Namespace, pagename: str, b: Buffer):
		entries: dict[str, bytes] = {}
		# Read # of entries
		n_entries = b.readInt()
		# For each entry
		for _ in range(n_entries):
			# Read name length
			namel = b.readInt()
			# Read name
			name = b.read(namel).decode("UTF-8")
			# Read value length
			vall = (((b.readInt() * 256) + b.readInt()) * 256) + b.readInt()
			# Read value
			val = b.read(vall)
			# Finish
			entries[name] = val
		return Page(ns, pagename, entries)

if __name__ == "__main__":
	ns = Namespace.fromFile("Main")
	if ns == None: exit()
	h = PageHistory(ns, "Main_Page", [
		("Create main page", Page(ns, "Main_Page", {
			"title": b"Main Page",
			"content": b"Some content"
		}))
	])
	h.save()
	# h = PageHistory.fromFile("Main:Main_Page")
	# print(h.data[0][1].data)
