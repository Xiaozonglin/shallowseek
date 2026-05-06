import os
from markitdown import MarkItDown

def convert_to_markdown(file_path: str) -> str:
    """
    将 PDF 或 Docx 转换为 Markdown
    """
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        return f"错误：文件 {file_path} 不存在"

    md = MarkItDown()

    try:
        print(f"正在转换: {os.path.basename(file_path)} ...")
        result = md.convert(abs_path)
        
        return result.markdown
    except Exception as e:
        return f"转换失败: {str(e)}"

if __name__ == "__main__":
    # 都需要使用绝对路径
    docx_md = convert_to_markdown("")

    pdf_md = convert_to_markdown("")

    with open("output.md", "w", encoding="utf-8") as f:
        f.write("# 转换结果\n\n")
        f.write("## DOCX 内容\n")
        f.write(docx_md)
        f.write("\n\n---\n\n")
        f.write("## PDF 内容\n")
        f.write(pdf_md)