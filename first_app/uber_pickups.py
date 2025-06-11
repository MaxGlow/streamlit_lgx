import streamlit as st
import os
import PyPDF2
from pathlib import Path
from tempfile import TemporaryDirectory
import base64
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="PDF处理工具 - 拆分与合并",
    page_icon="📄",
    layout="wide"
)

# 标题和介绍
st.title("PDF处理工具")
st.markdown("轻松实现PDF文件的拆分与合并功能")
st.write("---")


# 缓存资源以提高性能
@st.cache_resource
def get_pdf_processor():
    """初始化PDF处理相关资源"""
    return PyPDF2.PdfWriter(), PyPDF2.PdfReader


# 改进的下载文件函数 - 显示带文件名的下载链接
def get_download_link(file_path, file_name):
    """生成适用于Streamlit的下载链接，显示完整文件名"""
    try:
        # 确保文件存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 生成带时间戳的唯一文件名，避免缓存问题
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_file_name = f"{os.path.splitext(file_name)[0]}_{timestamp}{os.path.splitext(file_name)[1]}"

        # 为Streamlit生成Base64编码链接
        with open(file_path, "rb") as f:
            bytes_data = f.read()
        b64 = base64.b64encode(bytes_data).decode()

        # **关键修改点**：下载链接文本显示实际文件名
        download_text = f"下载处理后的文件：{unique_file_name}"
        streamlit_link = f'<a href="data:application/octet-stream;base64,{b64}" download="{unique_file_name}">{download_text}</a>'

        return streamlit_link, unique_file_name
    except Exception as e:
        st.error(f"生成下载链接时出错: {e}")
        return None, None


# PDF拆分功能
def pdf_splitter():
    """PDF文件拆分功能"""
    st.subheader("📄 PDF拆分")
    st.write("将PDF文件按指定页码范围拆分成多个文件")

    # 上传PDF文件
    uploaded_file = st.file_uploader("上传PDF文件", type=["pdf"], accept_multiple_files=False)

    if uploaded_file is not None:
        with TemporaryDirectory() as temp_dir:
            # 保存上传的文件到临时目录
            temp_dir_path = Path(temp_dir)
            temp_file = temp_dir_path / uploaded_file.name
            with open(temp_file, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # 读取PDF页数
            pdf_reader = PyPDF2.PdfReader(temp_file)
            total_pages = len(pdf_reader.pages)
            st.info(f"检测到PDF文件共有 {total_pages} 页")

            # 用户输入拆分方式
            split_method = st.radio("选择拆分方式", ["按页码范围拆分", "按每X页拆分"])

            if split_method == "按页码范围拆分":
                st.write("输入要拆分的页码范围（页码从1开始）")
                col1, col2 = st.columns(2)
                with col1:
                    start_page = st.number_input("起始页码", min_value=1, max_value=total_pages, value=1)
                with col2:
                    end_page = st.number_input("结束页码", min_value=start_page, max_value=total_pages,
                                               value=total_pages)

                if st.button("执行拆分"):
                    # 创建输出文件
                    output_file = temp_dir_path / f"拆分后的PDF_{start_page}-{end_page}.pdf"
                    pdf_writer = PyPDF2.PdfWriter()

                    # 按页码范围添加页面
                    for page_num in range(start_page - 1, end_page):  # PDF页码从0开始
                        pdf_writer.add_page(pdf_reader.pages[page_num])

                    # 保存拆分后的PDF
                    with open(output_file, "wb") as f:
                        pdf_writer.write(f)

                    st.success(f"已成功将第 {start_page} 页到第 {end_page} 页拆分为新PDF文件")

                    # 生成下载链接
                    streamlit_link, file_name = get_download_link(output_file,
                                                                  f"拆分后的PDF_{start_page}-{end_page}.pdf")

                    if streamlit_link:
                        st.markdown(streamlit_link, unsafe_allow_html=True)

            else:  # 按每X页拆分
                pages_per_file = st.number_input("每X页拆分为一个文件", min_value=1, value=5)

                if st.button("执行拆分"):
                    # 计算需要拆分的文件数
                    num_files = (total_pages + pages_per_file - 1) // pages_per_file
                    st.info(f"将拆分为 {num_files} 个PDF文件")

                    # 逐个拆分文件
                    for file_idx in range(num_files):
                        start_page = file_idx * pages_per_file + 1
                        end_page = min((file_idx + 1) * pages_per_file, total_pages)

                        output_file = temp_dir_path / f"拆分后的PDF_{start_page}-{end_page}.pdf"
                        pdf_writer = PyPDF2.PdfWriter()

                        for page_num in range(start_page - 1, end_page):
                            pdf_writer.add_page(pdf_reader.pages[page_num])

                        with open(output_file, "wb") as f:
                            pdf_writer.write(f)

                        # 生成下载链接
                        streamlit_link, file_name = get_download_link(output_file,
                                                                      f"拆分后的PDF_{start_page}-{end_page}.pdf")

                        if streamlit_link:
                            st.markdown(streamlit_link, unsafe_allow_html=True)


# PDF合并功能
def pdf_merger():
    """PDF文件合并功能"""
    st.subheader("📂 PDF合并")
    st.write("将多个PDF文件合并为一个PDF文件")

    # 上传多个PDF文件
    uploaded_files = st.file_uploader("上传多个PDF文件", type=["pdf"], accept_multiple_files=True)

    if uploaded_files is not None and len(uploaded_files) > 1:
        with TemporaryDirectory() as temp_dir:
            # 保存所有上传的文件到临时目录
            temp_dir_path = Path(temp_dir)
            temp_files = []
            for file in uploaded_files:
                temp_file = temp_dir_path / file.name
                with open(temp_file, "wb") as f:
                    f.write(file.getbuffer())
                temp_files.append(temp_file)

            if st.button("执行合并"):
                pdf_merger = PyPDF2.PdfMerger()

                # 按上传顺序添加PDF文件
                for file in temp_files:
                    pdf_merger.append(str(file))

                # 保存合并后的PDF
                output_file = temp_dir_path / "合并后的PDF.pdf"
                pdf_merger.write(str(output_file))
                pdf_merger.close()

                st.success(f"已成功合并 {len(uploaded_files)} 个PDF文件")

                # 生成下载链接
                streamlit_link, file_name = get_download_link(output_file, "合并后的PDF.pdf")

                if streamlit_link:
                    st.markdown(streamlit_link, unsafe_allow_html=True)

    elif uploaded_files is not None and len(uploaded_files) == 1:
        st.warning("请上传至少两个PDF文件进行合并")
    else:
        st.info("请上传需要合并的PDF文件（至少两个）")


# 主界面布局
def main():
    """主界面函数"""
    # 创建选项卡
    tab1, tab2 = st.tabs(["PDF拆分", "PDF合并"])

    with tab1:
        pdf_splitter()

    with tab2:
        pdf_merger()

    # 页脚
    st.write("---")
    st.write("© 2025 PDF处理工具 | 简单实用的PDF文件处理解决方案")


if __name__ == "__main__":
    main()