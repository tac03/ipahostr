#!/usr/bin/python3

import os
import shutil
import glob
import json
import plistlib
import http.server
import socketserver
import sys
import socket

host_port_num = 19494

# Static files (hardcoded into py file so it is portable)
indexPage = ("<html>"
			"<head>"
			"<title>ipahostr</title>"
			"<link rel='stylesheet' type='text/css' href='ipahostr.css'>"
			"</head>"
			"<body></body><script src='ipahostr.js'></script></html>")
cssFile = ("body { display: flex; align-items: flex-start; justify-content: flex-start }"
			"div.app-icon { display: flex; align-items: center; justify-content: flex-start; flex-direction: column; cursor: pointer; margin: 5px }"
			"div.app-icon div { width: 120px; height: 120px; }"
			"div.app-icon span { text-align: center; font-size: 16px; }")

jsFile = 'const req=new XMLHttpRequest;req.responseType="json",req.addEventListener("load",()=>{if(200!=req.status)return;let e=req.response;for(let n of e){const e=document.createElement("div");e.className="app-icon",e.innerHTML=`\n\t\t\t<div><img src="ipa/${n.name}/icon.png" alt="${n.name}" width="120" height="120" style="border-radius: 10px"></div>\n\t\t\t<span>${n.name} (${n.version})</span>\n\t\t`,e.addEventListener("click",()=>{const e=document.createElement("a");e.href=`itms-services://?action=download-manifest&url=${window.location.href}ipa/${n.name}/manifest.plist`,e.click(),e.remove()}),document.body.appendChild(e)}}),req.open("GET","ipa/contents.json"),req.send();'


class IPAServer(http.server.SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, directory="ipahostr", **kwargs)


def main(argv):
	server_host = f"http://{socket.gethostbyname(socket.gethostname())}/{host_port_num}" if len(argv) == 0 else argv[0]

	print("[*] Looking for 'ipahostr' folder...")
	if not os.path.isdir("ipahostr"):
		print("[*] No 'ipahostr' folder found! Looking for .app files...")
		appFiles = glob.glob("*.app")
		appCount = len(appFiles)

		if appCount == 0:
			print("[!] No .app files found! Exiting...")
			return

		appOrApps = "apps" if appCount > 1 else "app"
		print(f"[*] Found {appCount} {appOrApps}! Generating 'ipahostr' folder...")

		# Create 'ipahostr' folder
		os.mkdir("ipahostr")

		# Generate 'index.html'
		indexPath = os.path.join("ipahostr", "index.html")
		with open(indexPath, "w") as fp:
			fp.write(indexPage)

		# Generate 'ipahostr.css'
		cssPath = os.path.join("ipahostr", "ipahostr.css")
		with open(cssPath, "w") as fp:
			fp.write(cssFile)

		# Generate 'ipahostr.js'
		jsPath = os.path.join("ipahostr", "ipahostr.js")
		with open(jsPath, "w") as fp:
			fp.write(jsFile)

		# Create 'ipa' folder
		ipaDir = os.path.join("ipahostr", "ipa")
		os.mkdir(ipaDir)

		# Process apps
		contentsJson = []
		for app in appFiles:
			print(f"[*] Processing {app}...")

			appName = app.split(".")[0]
			appDir = os.path.join(ipaDir, appName)

			# Check if 'Info.plist' exists
			infoPlistPath = os.path.join(app, "Info.plist")
			if not os.path.isfile(infoPlistPath):
				print("[!] No 'Info.plist' file found! Skipping...")
				continue

			# Create folder
			os.mkdir(appDir)

			# Copy 'Icon-60@2x.png' if exists
			srcIconPath = os.path.join(app, "Icon-60@2x.png")
			if os.path.isfile(srcIconPath):
				dstIconPath = os.path.join(appDir, "icon.png")
				shutil.copyfile(srcIconPath, dstIconPath)

			# Load values from info plist
			infoPlist = None
			with open(infoPlistPath, "rb") as fp:
				infoPlist = plistlib.load(fp)
			appVersion = infoPlist["CFBundleShortVersionString"]
			appBundleId = infoPlist["CFBundleIdentifier"]

			# Add entry to contentsJson
			contentsJson.append({
				"name": appName,
				"version": appVersion
			})

			# Generate manifest.plist
			manifestPlist = {
				"items": [
					{
						"assets": [
							{
								"kind": "software-package",
								"url": f"{server_host}/ipa/{appName}/{appName}.ipa"
							}
						],
						"metadata": {
							"bundle-identifier": appBundleId,
							"bundle-version": appVersion,
							"kind": "software",
							"title": appName
						}
					}
				]
			}
			dstManifestPlist = os.path.join(appDir, "manifest.plist")
			with open(dstManifestPlist, "wb") as fp:
				plistlib.dump(manifestPlist, fp)

			# Create 'Payload' folder (wrap)
			payloadFolder = os.path.join(appDir, "Payload")
			os.mkdir(payloadFolder)

			# Create 'Payload' folder (child)
			childPayloadFolder = os.path.join(payloadFolder, "Payload")
			os.mkdir(childPayloadFolder)

			# Copy '.app' to 'Payload' folder
			dstAppDir = os.path.join(childPayloadFolder, app)
			shutil.copytree(app, dstAppDir)

			# Create '.ipa' from 'Payload' (wrap)
			dstIPAFile = os.path.join(appDir, appName + ".ipa")
			shutil.make_archive(dstIPAFile, "zip", payloadFolder)

			# Remove .zip extension
			os.rename(dstIPAFile + ".zip", dstIPAFile)

			# Delete 'Payload' folder
			shutil.rmtree(payloadFolder)
		
		print("[*] Generating 'contents.json'...")
		contentsJsonPath = os.path.join(ipaDir, "contents.json")
		with open(contentsJsonPath, "w") as fp:
			json.dump(contentsJson, fp)

	print("[*] Starting server...")
	with socketserver.TCPServer(("", host_port_num), IPAServer) as httpd:
		print(f"[*] Serving at http://[::]:{host_port_num}...")
		httpd.serve_forever()


if __name__ == "__main__":
	main(sys.argv[1:])
