import trafilatura

url = "https://www.xiaozonglin.cn/spark-bei-participate-small-ji/"
downloaded = trafilatura.fetch_url(url)

# 核心功能：直接提取正文并转化为 Markdown
# include_tables=True 保留表格
# include_links=True 保留链接
markdown_content = trafilatura.extract(downloaded, output_format='markdown', include_tables=True, include_links=True)

print(markdown_content)