import streamlit as st
import pandas as pd

st.set_page_config(page_title="Excel差异检查", layout="wide")
st.title("📊 Excel 文件差异检查（简单模式）")

st.markdown("""
本工具对比两个 Excel 文件的差异，基于整行内容（顺序无关）：

- ✅ 新增的行（文件2中出现但文件1没有）
- ✅ 删除的行（文件1中有但文件2没有）
- ✅ 每行前面会显示原始 Excel 中的**行号**
- ✅ 支持多行选择进行内容比对
""")

file1 = st.file_uploader("上传 Excel 文件 1", type=["xlsx", 'xlsm'], key="file1")
file2 = st.file_uploader("上传 Excel 文件 2", type=["xlsx", 'xlsm'], key="file2")

@st.cache_data(show_spinner=False)
def load_excel(file1, file2):
    return compare_excel_simple_with_lineno(file1, file2)

def get_row_map(df):
    df = df.fillna("").astype(str)
    row_map = {}
    for i, row in df.iterrows():
        key = tuple(row)
        if key not in row_map:
            row_map[key] = i + 2  # Excel 行号（从 2 开始，考虑表头）
    return row_map

def compare_excel_simple_with_lineno(file1, file2):
    xl1 = pd.ExcelFile(file1, engine="openpyxl")
    xl2 = pd.ExcelFile(file2, engine="openpyxl")

    result = {}
    sheets1 = set(xl1.sheet_names)
    sheets2 = set(xl2.sheet_names)

    result["sheet_diff"] = {
        "only_in_file1": list(sheets1 - sheets2),
        "only_in_file2": list(sheets2 - sheets1),
    }

    common_sheets = sheets1 & sheets2
    sheet_changes = {}

    for sheet in common_sheets:
        df1 = xl1.parse(sheet).fillna("").astype(str)
        df2 = xl2.parse(sheet).fillna("").astype(str)

        rows1 = get_row_map(df1)
        rows2 = get_row_map(df2)

        set1 = set(rows1.keys())
        set2 = set(rows2.keys())

        deleted = [(rows1[row], row) for row in set1 - set2]
        added = [(rows2[row], row) for row in set2 - set1]

        if deleted or added:
            sheet_changes[sheet] = {
                "columns": df1.columns.tolist() if not df1.empty else df2.columns.tolist(),
                "added": sorted(added, key=lambda x: x[0]),
                "deleted": sorted(deleted, key=lambda x: x[0])
            }

    result["sheet_changes"] = sheet_changes
    return result

def render_row_table_with_checkbox(title, rows_with_lineno, columns, key_prefix):
    if not rows_with_lineno:
        return []

    st.markdown(f"**{title}**")

    data = []
    for lineno, row in rows_with_lineno:
        row_dict = {"选择": False, "原始行号": lineno}
        row_dict.update({col: val for col, val in zip(columns, row)})
        data.append(row_dict)

    df_display = pd.DataFrame(data)
    edited_df = st.data_editor(
        df_display,
        use_container_width=True,
        key=key_prefix,
        hide_index=True,
        column_config={"选择": st.column_config.CheckboxColumn(label="选择")}
    )

    selected_rows = []
    for _, row in edited_df.iterrows():
        if row["选择"]:
            selected = tuple(row[col] for col in columns)
            selected_rows.append(selected)

    return selected_rows

def compare_selected_rows(added, deleted, columns):
    st.subheader("🟡 选中行详细比对")
    if len(added) != len(deleted):
        st.error("⚠️ 选中的新增行与删除行数量不一致，无法逐行比对。")
        return

    html = "<div style='overflow-x:auto'><table style='border-collapse: collapse; font-size: 14px;'>"
    html += ("<tr><th style='border:1px solid #ccc;padding:6px;background-color:#f0f0f0'>类型</th>"
             + "".join(f"<th style='border:1px solid #ccc;padding:6px;background-color:#f0f0f0'>{col}</th>" for col in columns)
             + "</tr>")

    for idx in range(len(added)):
        row1 = deleted[idx]
        row2 = added[idx]

        html += "<tr><td style='border:1px solid #ccc;padding:6px;'>删除行</td>"
        for i in range(len(columns)):
            color = "#ffd6d6" if row1[i] != row2[i] else "#ffffff"
            html += f"<td style='border:1px solid #ccc;padding:6px;background-color:{color}'>{row1[i]}</td>"
        html += "</tr>"

        html += "<tr><td style='border:1px solid #ccc;padding:6px;'>新增行</td>"
        for i in range(len(columns)):
            color = "#d6f5d6" if row1[i] != row2[i] else "#ffffff"
            html += f"<td style='border:1px solid #ccc;padding:6px;background-color:{color}'>{row2[i]}</td>"
        html += "</tr>"

    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)

# 主逻辑
if file1 and file2:
    st.header("📄 Sheet 名称差异")
    if st.button("加载并分析文件差异"):
        result = load_excel(file1, file2)
        st.session_state.result_data = result
    elif "result_data" in st.session_state:
        result = st.session_state.result_data
    else:
        st.stop()

    st.write("✅ 仅在 文件1 中的 Sheet：", result["sheet_diff"]["only_in_file1"])
    st.write("✅ 仅在 文件2 中的 Sheet：", result["sheet_diff"]["only_in_file2"])

    st.header("🔍 内容差异（基于整行内容，忽略顺序）")
    if not result["sheet_changes"]:
        st.success("所有 Sheet 内容完全一致 ✅")
    else:
        for sheet_name, info in result["sheet_changes"].items():
            st.subheader(f"📘 Sheet：`{sheet_name}`")
            selected_added = render_row_table_with_checkbox(
                "🟢 新增行（文件2有，文件1无）", info["added"], info["columns"], f"added_{sheet_name}"
            )
            selected_deleted = render_row_table_with_checkbox(
                "🔴 删除行（文件1有，文件2无）", info["deleted"], info["columns"], f"deleted_{sheet_name}"
            )

            if st.button(f"对比选中行 - Sheet：{sheet_name}"):
                compare_selected_rows(selected_added, selected_deleted, info["columns"])
