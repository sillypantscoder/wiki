class TextSpan:
	def __init__(self, t: str):
		self.t = t
	def toHTML(self):
		return self.t
	@staticmethod
	def read(line: str, raw: bool) -> "tuple[list[TextSpan], bool]":
		spans: "list[TextSpan]" = []
		currentType: "type[TextSpan]" = TextSpan
		if raw: currentType = TextSpanRaw
		current = ""
		i = 0
		while i < len(line):
			if line[i:i + len("$END")] == "$END":
				spans.append(currentType(current))
				current = ""
				i += len("$END") - 1
				currentType = TextSpanRaw
			elif line[i:i + len("$START")] == "$START":
				spans.append(currentType(current))
				current = ""
				i += len("$START") - 1
				currentType = TextSpan
			elif currentType == TextSpanRaw:
				current += line[i]
			elif line[i] == "*":
				spans.append(currentType(current))
				current = ""
				if currentType == TextSpanBold:
					currentType = TextSpan
				else:
					currentType = TextSpanBold
			elif line[i] == "_":
				spans.append(currentType(current))
				current = ""
				if currentType == TextSpanItalic:
					currentType = TextSpan
				else:
					currentType = TextSpanItalic
			elif line[i:i + 2] == "[[":
				spans.append(currentType(current))
				current = ""
				# Get the link data
				idata = ""
				i += 2
				while line[i:i + 2] != "]]":
					idata += line[i]
					i += 1
				i += 1
				# Add the span
				spans.append(TextSpanLink(idata, "/wiki/" + idata))
			else:
				current += line[i]
			i += 1
		spans.append(currentType(current))
		return (spans, currentType == TextSpanRaw)

class TextSpanRaw(TextSpan):
	pass

class TextSpanBold(TextSpan):
	def toHTML(self):
		return f"<b>{self.t}</b>"

class TextSpanItalic(TextSpan):
	def toHTML(self):
		return f"<i>{self.t}</i>"

class TextSpanLink(TextSpan):
	def __init__(self, t: str, href: str):
		super().__init__(t)
		self.href = href
	def toHTML(self):
		return f"<a href=\"{self.href}\">{self.t}</a>"

class Paragraph:
	def __init__(self, t: list[TextSpan]):
		self.spans = t
	def getPrefix(self) -> str:
		return "<p>"
	def getSuffix(self) -> str:
		return "</p>"
	def toHTML(self):
		r: str = self.getPrefix()
		for s in self.spans:
			r += s.toHTML()
		r += self.getSuffix()
		return r

class Heading1(Paragraph):
	def getPrefix(self):
		return "<h1>"
	def getSuffix(self):
		return "</h1>"

def parse(inputStr: str) -> list[Paragraph]:
	lines = inputStr.split("\n")
	paras: list[Paragraph] = []
	raw = False
	for line in lines:
		if line == "": continue
		if line.startswith("# "):
			info = TextSpan.read(line[2:], raw)
			raw = info[1]
			paras.append(Heading1(info[0]))
		else:
			info = TextSpan.read(line, raw)
			raw = info[1]
			paras.append(Paragraph(info[0]))
	return paras

def wtToHTML(inputStr: str) -> str:
	paras = parse(inputStr)
	r = [x.toHTML() for x in paras]
	return "".join(r)

if __name__ == "__main__":
	# s = TextSpan.read("Hi *there* whee")
	# print("".join([x.toHTML() for x in s]))
	print(wtToHTML("# hi"))
