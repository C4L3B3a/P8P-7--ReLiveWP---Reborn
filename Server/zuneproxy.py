import http.server
import socketserver
import urllib.parse
import os
import http.client
import ssl

PORT = 8080
BASE_PATH = "/.zune_files/"  # Folder with XML/PNG/XAP files

class ZuneProxyHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        url_path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)
        hostname = parsed_url.hostname
        scheme = parsed_url.scheme or "http"

        print(f"Incoming request: {self.path}")

        # If full URL with hostname and not a known Zune domain, proxy external request
        if hostname and hostname not in ("catalog.zune.net", "image.catalog.zune.net"):
            self.proxy_external_request(parsed_url)
            return

        # Mapping known Zune catalog URLs to local files

        # Marketplace hub
        if url_path.startswith("/v3.2/en-US/clientTypes/WinMobile 7.1/hubTypes/marketplace/hub"):
            self.serve_local_file("marketplacehub.xml")
            return

        # Apps hub
        if url_path.startswith("/v3.2/en-US/clientTypes/WinMobile 7.1/hubTypes/apps/hub"):
            self.serve_local_file("appshub.xml")
            return

        # Games hub
        if url_path.startswith("/v3.2/en-US/clientTypes/WinMobile 7.1/hubTypes/games/hub"):
            self.serve_local_file("gameshub.xml")
            return

        # Music hub (if you have musichub.xml)
        if url_path.startswith("/v3.2/en-US/hubs/music"):
            self.serve_local_file("musichub.xml")
            return

        # App categories
        if url_path.startswith("/v3.2/en-US/appCategories"):
            self.serve_local_file("appcatagories.xml")
            return

        # Specific app info: /apps/[UUID]
        if url_path.startswith("/v3.2/en-US/apps/"):
            parts = url_path.split('/')
            if len(parts) > 4:
                app_uuid = parts[4]
                # /apps/[UUID]/primaryImage
                if len(parts) > 5 and parts[5] == "primaryImage":
                    # Serve PNG image file for app icon
                    image_file = f"app_{app_uuid}.png"
                    self.serve_local_file(image_file)
                    return

                # /apps/[UUID]/reviews
                if len(parts) > 5 and parts[5] == "reviews":
                    # TODO: Implement review XML if available
                    # For now, return 404 to avoid stub
                    self.send_error(404, "Reviews XML not implemented")
                    return

                # /apps/[UUID] main info XML
                if len(parts) == 5:
                    xml_file = f"app_{app_uuid}.xml"
                    self.serve_local_file(xml_file)
                    return

        # Images: /image/[UUID]?params
        if url_path.startswith("/v3.2/en-US/image/"):
            img_uuid = url_path.split('/')[-1]
            image_file = f"app_{img_uuid}.png"
            self.serve_local_file(image_file)
            return

        # If nothing matched, 404
        self.send_error(404, f"No mapping for {url_path}")

    def serve_local_file(self, filename):
        full_path = os.path.join(BASE_PATH, filename)
        if os.path.isfile(full_path):
            print(f"Served local file: {full_path}")
            self.send_response(200)
            # Basic content type based on extension
            if filename.endswith(".xml"):
                self.send_header("Content-Type", "application/xml")
            elif filename.endswith(".png"):
                self.send_header("Content-Type", "image/png")
            else:
                self.send_header("Content-Type", "application/octet-stream")
            self.end_headers()
            with open(full_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            print(f"File missing: {full_path}")
            self.send_error(404, f"File missing: {filename}")

    def proxy_external_request(self, parsed_url):
        try:
            port = parsed_url.port
            if not port:
                port = 443 if parsed_url.scheme == "https" else 80

            if parsed_url.scheme == "https":
                conn = http.client.HTTPSConnection(parsed_url.hostname, port, context=ssl._create_unverified_context())
            else:
                conn = http.client.HTTPConnection(parsed_url.hostname, port)

            path_with_query = parsed_url.path
            if parsed_url.query:
                path_with_query += "?" + parsed_url.query

            # Prepare headers (remove host to let connection set it)
            headers = dict(self.headers)
            headers.pop("Host", None)

            conn.request("GET", path_with_query, headers=headers)
            resp = conn.getresponse()

            self.send_response(resp.status, resp.reason)
            for header, value in resp.getheaders():
                if header.lower() not in ("transfer-encoding", "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "upgrade"):
                    self.send_header(header, value)
            self.end_headers()

            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)

            conn.close()
            print(f"Proxied external URL: {parsed_url.geturl()}")
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")


if __name__ == "__main__":
    with socketserver.ThreadingTCPServer(("", PORT), ZuneProxyHandler) as httpd:
        print(f"P8P 7: ReLiveWP - Reborn | Marketplace XML proxy running at http://localhost:{PORT}")
        httpd.serve_forever()

# Script made by HRZ456.ipa (hrz456)