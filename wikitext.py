class TextSpan:
	def __init__(self, t: str):
		self.t = t
	def toHTML(self):
		return self.t
	@staticmethod
	def read(line: str):
		spans: "list[TextSpan]" = []
		currentType: "type[TextSpan]" = TextSpan
		current = ""
		i = 0
		while i < len(line):
			if line[i] == "*":
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
			else:
				current += line[i]
			i += 1
		spans.append(currentType(current))
		return spans

class TextSpanBold(TextSpan):
	def toHTML(self):
		return f"<b>{self.t}</b>"

class TextSpanItalic(TextSpan):
	def toHTML(self):
		return f"<i>{self.t}</i>"

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
	for line in lines:
		if line == "": continue
		if line.startswith("# "):
			paras.append(Heading1(TextSpan.read(line[2:])))
		else:
			paras.append(Paragraph(TextSpan.read(line)))
	return paras

def wtToHTML(inputStr: str) -> str:
	paras = parse(inputStr)
	r = [x.toHTML() for x in paras]
	return "".join(r)

if __name__ == "__main__":
	s = TextSpan.read("Hi *there* whee")
	print("".join([x.toHTML() for x in s]))
