import utils
import json

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

class Namespace:
	def __init__(self, name: str, fields: list[str], content: str):
		self.name = name
		self.fields = fields
		self.content = content
	@staticmethod
	def fromFile(name: str):
		data = json.loads(utils.read_file(f"pages/{name}/ns.json"))
		return Namespace(name, data["fields"], data["content"])
	def getContent(self, page: "Page"):
		r = ""
		charno = 0
		while charno < len(self.content):
			char = self.content[charno]
			if self.content[charno:charno + len("{{field ")] == "{{field ":
				charno += len("{{field ")
				name = ""
				while self.content[charno] != " ":
					name += self.content[charno]
					charno += 1
				charno += 1
				defaultval = ""
				while self.content[charno:charno + 2] != "}}":
					defaultval += self.content[charno]
					charno += 1
				charno += 1
				# Substitute the data
				if name in page.data.keys():
					r += page.data[name].decode("UTF-8")
				else:
					r += defaultval
			else:
				r += char
			charno += 1
		return r

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
	def fromFile(name: str):
		ns = name.split(":")[0]
		pn = name.split(":")[1]
		nso = Namespace.fromFile(ns)
		raw = Buffer(utils.read_file(f"pages/{ns}/{pn}.dat"))
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
		return self.data[-1][1]

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
			r.append(0)
			r.append(0) # TODO: Value length is 3 bytes?
			r.append(len(value))
			# Write value
			r.extend([*value])
		return r
	@staticmethod
	def read(ns: Namespace, name: str, b: Buffer):
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
		return Page(ns, name, entries)

if __name__ == "__main__":
	ns = Namespace.fromFile("Main")
	h = PageHistory(ns, "Main_Page", [
		("Create main page", Page(ns, "Main_Page", {
			"title": b"Main Page",
			"content": b"Some content"
		}))
	])
	h.save()
	# h = PageHistory.fromFile("Main:Main_Page")
	# print(h.data[0][1].data)