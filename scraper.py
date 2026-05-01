import re
import js
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup 

ALLOWED_DOMAINS = {
    "ics.uci.edu",
    "cs.uci.edu",
    "informatics.uci.edu",
    "stat.uci.edu",
}

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "were", "will", "with", "or", "not", "this", "but",
    "you", "your", "we", "our", "they", "their", "can", "all", "if",
    "more", "about", "which", "when", "who", "what", "where", "how"
}

visited_urls = set()
word_counter = Counter()
subdomain_counter = defaultdict(int)
longest_page_url = ""
longest_page_word_count = 0

def scraper(url, resp):
    links = extract_next_links(url, resp)
    save_report_data()
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    if resp is None or resp.status != 200:
        return list()

    if resp.raw_response is None or resp.raw_response.content is None:
        return list()

	clean_current_url, _ = urldefrag(url)

	if clean_current_url not in visited_urls:
        visited_urls.add(clean_current_url)
        update_report_data(clean_current_url, resp.raw_response.content)

    soup = BeautifulSoup(resp.raw_response.content, "html.parser")
    links = list()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        if href == "":
            continue

        absolute_url = urljoin(url, href)
        clean_url, _ = urldefrag(absolute_url)

        links.append(clean_url)

    return links


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
       parsed = urlparse(url)

        if parsed.scheme not in set(["http", "https"]):
            return False

        domain = parsed.netloc.lower()

        if not any(domain == allowed or domain.endswith("." + allowed)
                   for allowed in ALLOWED_DOMAINS):
            return False

		if len(url) > 300:
            return False

        if has_repeated_path_segments(parsed.path):
            return False

        if parsed.query.count("&") > 5:
            return False

        if has_trap_pattern(url):
            return False
	
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
		return False

def update_report_data(url, html_content):
    global longest_page_url
    global longest_page_word_count

    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    words = re.findall(r"[a-zA-Z]+", text.lower())

    useful_words = [word for word in words if word not in STOP_WORDS and len(word) > 1]

    word_counter.update(useful_words)

    if len(useful_words) > longest_page_word_count:
        longest_page_word_count = len(useful_words)
        longest_page_url = url

    subdomain = urlparse(url).netloc.lower()
    subdomain_counter[subdomain] += 1


def save_report_data():
    data = {
        "unique_pages": len(visited_urls),
        "longest_page": {
            "url": longest_page_url,
            "word_count": longest_page_word_count
        },
        "top_50_words": word_counter.most_common(50),
        "subdomains": dict(sorted(subdomain_counter.items()))
    }

    with open("crawl_report_data.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)


def has_repeated_path_segments(path):
    parts = [part for part in path.lower().split("/") if part]

    counts = Counter(parts)

    for count in counts.values():
        if count >= 3:
            return True

    return False


def has_trap_pattern(url):
    lowered_url = url.lower()

    trap_patterns = [
        "calendar",
        "date=",
        "year=",
        "month=",
        "replytocom",
        "sessionid",
        "sid=",
        "sort=",
        "filter="
    ]

    return any(pattern in lowered_url for pattern in trap_patterns)
