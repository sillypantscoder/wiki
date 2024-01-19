from http.server import BaseHTTPRequestHandler, HTTPServer
import typing
import wiki
import wikitext
import utils
import json

hostName = "0.0.0.0"
serverPort = 8080

class HTTPResponse(typing.TypedDict):
	status: int
	headers: dict[str, str]
	content: bytes

class HTTPDirective:
	def __init__(self):
		self.directions: "dict[str, HTTPDirective] | typing.Callable[[ str, bytes ], HTTPResponse]" = {}
	def then(self, name: str):
		n = HTTPDirective()
		if isinstance(self.directions, dict):
			self.directions[name] = n
		return n
	def run(self, func: typing.Callable[[ str, bytes ], HTTPResponse]):
		self.directions = func
	def after(self, name: str):
		if isinstance(self.directions, dict):
			return self.directions[name]
		else:
			return self
	def get(self, path: list[str], body: bytes) -> HTTPResponse | None:
		if len(path) == 0:
			if not isinstance(self.directions, dict):
				return self.directions("/".join(path), body)
		else:
			if isinstance(self.directions, dict):
				if path[0] in self.directions.keys():
					return self.directions[path[0]].get(path[1:], body)
			else:
				return self.directions("/".join(path), body)
	def root_get(self, _path: str) -> HTTPResponse:
		path = _path[1:]
		path = path.split("?")[0]
		path = path.split("/") if len(path) > 0 else []
		res = self.get(path, "?".join(_path.split("?")[1:]).encode("UTF-8"))
		r: HTTPResponse = {
			"status": 404,
			"headers": {
				"Content-Type": "text/plain"
			},
			"content": f"404 GET {_path}".encode("UTF-8")
		}
		if res != None: r = res
		return r
	def root_post(self, _path: str, body: bytes) -> HTTPResponse:
		path = _path[1:]
		path = path.split("/") if len(path) > 0 else []
		res = self.get(path, body)
		r: HTTPResponse = {
			"status": 404,
			"headers": {
				"Content-Type": "text/plain"
			},
			"content": f"404 GET {_path}".encode("UTF-8")
		}
		if res != None: r = res
		return r

def getWiki(path: str, body: bytes) -> HTTPResponse:
	if len(path.split(":")) == 1:
		# A single name...
		# Check if this name is a namespace
		ns = wiki.Namespace.fromFile(path)
		if ns != None:
			# Return the default page
			return {
				"status": 302,
				"headers": {
					"Location": "/wiki/" + ns.name + ":" + ns.defaultPage
				},
				"content": b""
			}
		# Check if this is a page in the default namespace
		config = utils.read_file("settings.json")
		assert config != None
		return {
			"status": 302,
			"headers": {
				"Location": "/wiki/" + json.loads(config)["defaultNS"]
			},
			"content": b""
		}
	history = wiki.PageHistory.fromFile(path)
	if history == None:
		return {
			"status": 404,
			"headers": {
				"Content-Type": "text/html"
			},
			"content": b""
		}
	page: wiki.Page = history.mostRecent()
	content: str = wikitext.wtToHTML(page.getContent())
	return {
		"status": 200,
		"headers": {
			"Content-Type": "text/html"
		},
		"content": f"""<!DOCTYPE html>
<html>
	<head>
		<link href="/style.css" rel="stylesheet">
	</head>
	<body>
		{content}
	</body>
</html>""".encode("UTF-8")
	}

def getEditSelect(path: str, body: bytes) -> HTTPResponse:
	if len(path.split(":")) == 1:
		# aaaaaa
		return {
			"status": 404,
			"headers": {},
			"content": b""
		}
	history = wiki.PageHistory.fromFile(path)
	if history == None:
		return {
			"status": 404,
			"headers": {},
			"content": b""
		}
	return {
		"status": 200,
		"headers": {
			"Content-Type": "text/html"
		},
		"content": f"""<!DOCTYPE html>
<html>
	<head>
		<link href="/style.css" rel="stylesheet">
	</head>
	<body>
		<div class="sidebar">
			<a href="/wiki/{path}">Cancel - Back to page</a>
		</div>
		<div class="main-content">
			<h3>Edit {path}</h3>
			{"".join(['<p><a href="/edit/content/' + path + '/' + contentname + '">Edit ' + contentname + '</a></p>' for contentname in history.ns.fields])}
		</div>
	</body>
</html>""".encode("UTF-8")
	}

def getEditContent(path: str, body: bytes) -> HTTPResponse:
	name = path.split("/")[0]
	contentname = path.split("/")[1]
	if len(name.split(":")) == 1:
		# aaaaaa
		return {
			"status": 404,
			"headers": {},
			"content": b""
		}
	history = wiki.PageHistory.fromFile(name)
	if history == None:
		return {
			"status": 404,
			"headers": {},
			"content": b""
		}
	return {
		"status": 200,
		"headers": {
			"Content-Type": "text/html"
		},
		"content": f"""<!DOCTYPE html>
<html>
	<head>
		<link href="/style.css" rel="stylesheet">
	</head>
	<body>
		<div class="sidebar">
			<a href="/wiki/{name}" class="back_link">Cancel - Back to page</a>
		</div>
		<div class="main-content">
			<h3>Edit {contentname} of {name}</h3>
			<p><textarea id="content" value="Loading..." disabled></textarea></p>
			<p>Enter a message for your changes: <input id="message"></p>
			<p><button onclick="saveEdit()">Save</button></p>
		</div>
		<script>
(() => {{
	var x = new XMLHttpRequest();
	x.open("GET", "/get_data/{name}/{contentname}")
	x.addEventListener("loadend", () => {{
		document.querySelector("#content").value = x.responseText
		document.querySelector("#content").disabled = false
	}})
	x.send()
}})();
function saveEdit() {{
	var content = document.querySelector("#content").value
	var message = document.querySelector("#message").value
	var x = new XMLHttpRequest()
	x.open("POST", "/edit/{name}/{contentname}")
	x.addEventListener("loadend", () => {{
		document.querySelector(".back_link").click()
	}})
	x.send(message + "\\n" + content)
}}
		</script>
	</body>
</html>""".encode("UTF-8")
	}

def getData(path: str, body: bytes) -> HTTPResponse:
	name = path.split("/")[0]
	contentname = path.split("/")[1]
	if len(name.split(":")) == 1:
		# aaaaaa
		return {
			"status": 404,
			"headers": {},
			"content": b""
		}
	history = wiki.PageHistory.fromFile(name)
	if history == None:
		return {
			"status": 404,
			"headers": {},
			"content": b""
		}
	pageData = history.mostRecent().data
	return {
		"status": 200,
		"headers": {
			"Content-Type": "text/plain"
		},
		"content": pageData[contentname] if contentname in pageData.keys() else b""
	}

GET = HTTPDirective()
GET.then("style.css").run(lambda path, body: {
	"status": 200,
	"headers": {
		"Content-Type": "text/css"
	},
	"content": utils.optional(utils.read_file("style.css"), b"")
})
GET.then("wiki").run(getWiki)
GET.then("edit").then("select").run(getEditSelect)
GET.after("edit").then("content").run(getEditContent)
GET.then("get_data").run(getData)

def postEdit(path: str, body: bytes) -> HTTPResponse:
	name = path.split("/")[0]
	contentname = path.split("/")[1]
	message = body.split(b"\n")[0].decode("UTF-8")
	newcontent = b"\n".join(body.split(b"\n")[1:])
	if len(name.split(":")) == 1:
		# aaaaaa
		return {
			"status": 404,
			"headers": {},
			"content": b""
		}
	history = wiki.PageHistory.fromFile(name)
	if history == None:
		return {
			"status": 404,
			"headers": {},
			"content": b""
		}
	history.appendEdit(message, contentname, newcontent)
	history.save()
	return {
		"status": 200,
		"headers": {},
		"content": b""
	}

POST = HTTPDirective()
POST.then("edit").run(postEdit)

class MyServer(BaseHTTPRequestHandler):
	def do_GET(self):
		global running
		res = GET.root_get(self.path)
		self.send_response(res["status"])
		for h in res["headers"]:
			self.send_header(h, res["headers"][h])
		self.end_headers()
		c = res["content"]
		if isinstance(c, str): c = c.encode("utf-8")
		self.wfile.write(c)
	def do_POST(self):
		res = POST.root_post(self.path, self.rfile.read(int(self.headers["Content-Length"])))
		self.send_response(res["status"])
		for h in res["headers"]:
			self.send_header(h, res["headers"][h])
		self.end_headers()
		c = res["content"]
		if isinstance(c, str): c = c.encode("utf-8")
		self.wfile.write(c)
	def log_message(self, format: str, *args: typing.Any) -> None:
		return;
		if 400 <= int(args[1]) < 500:
			# Errored request!
			print(u"\u001b[31m", end="")
		print(args[0].split(" ")[0], "request to", args[0].split(" ")[1], "(status code:", args[1] + ")")
		print(u"\u001b[0m", end="")
		# don't output requests

if __name__ == "__main__":
	running = True
	webServer = HTTPServer((hostName, serverPort), MyServer)
	webServer.timeout = 1
	print("Server started http://%s:%s" % (hostName, serverPort))
	while running:
		try:
			webServer.handle_request()
		except KeyboardInterrupt:
			running = False
	webServer.server_close()
	print("Server stopped")
