"""Sinh file Huong_dan_su_dung_V3_v3.0.0.docx — bản release V3 (OneDir, giao diện TopBar).

Chạy: .venv\\Scripts\\python.exe docs\\gen_hdsd_v3.py
"""
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = "docs/Huong_dan_su_dung_V3_v3.0.0.docx"
FONT = "Times New Roman"

doc = Document()

# --- Style chuẩn: Times New Roman, size 14 ---
style = doc.styles["Normal"]
style.font.name = FONT
style.font.size = Pt(14)
style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
style.element.rPr.rFonts.set(qn("w:cs"), FONT)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = 1.15

for i, sz in ((1, 16), (2, 15), (3, 14)):
    hs = doc.styles[f"Heading {i}"]
    hs.font.name = FONT
    hs.font.size = Pt(sz)
    hs.font.bold = True
    hs.font.color.rgb = RGBColor(0x15, 0x24, 0x3F)
    hs.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    hs.element.rPr.rFonts.set(qn("w:cs"), FONT)

for st_name in ("List Bullet", "List Number"):
    try:
        ls = doc.styles[st_name]
        ls.font.name = FONT
        ls.font.size = Pt(14)
    except KeyError:
        pass


def shade(par, fill="D9D9D9"):
    pPr = par._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def body(text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = FONT
    r.font.size = Pt(14)
    return p


def add_placeholder(doc, code, filename, caption, how, width_cm):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    shade(p)
    r = p.add_run(f"[CHÈN ẢNH {code}: {filename}]")
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    r.font.name = FONT
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run(f"Hình {code} – {caption}. | {how} | Cỡ hiển thị: rộng {width_cm}. Xóa dòng này sau khi chèn ảnh.")
    r2.italic = True
    r2.font.size = Pt(12)
    r2.font.color.rgb = RGBColor(0x59, 0x59, 0x59)
    r2.font.name = FONT
    return p


def bullet(text, bold_head=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_head:
        r = p.add_run(bold_head)
        r.bold = True
        r.font.name = FONT
        r.font.size = Pt(14)
        r2 = p.add_run(text)
        r2.font.name = FONT
        r2.font.size = Pt(14)
    else:
        r = p.add_run(text)
        r.font.name = FONT
        r.font.size = Pt(14)
    return p


def table(headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        c = t.cell(0, j)
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(14)
        r.font.name = FONT
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            r = c.paragraphs[0].add_run(val)
            r.font.size = Pt(14)
            r.font.name = FONT
    doc.add_paragraph()
    return t


# ================= BÌA =================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run("PHẦN MỀM CHUYỂN ĐỔI VĂN BẢN THÀNH GIỌNG NÓI TỰ NHIÊN v3")
r.bold = True
r.font.size = Pt(20)
r.font.name = FONT
r.font.color.rgb = RGBColor(0x15, 0x24, 0x3F)

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("HƯỚNG DẪN SỬ DỤNG\nBẢN V3.0.0 – Dành cho người mới")
r.font.size = Pt(14)
r.font.name = FONT

info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = info.add_run("Tài liệu này dùng cho bản phát hành v3 chạy trực tiếp bằng file .exe, không cần cài Python, "
                 "không cần mạng (model giọng đọc đã nằm sẵn trong bản phát hành).\n"
                 "Tài liệu có sẵn 11 khung chờ ảnh, bạn tự chụp và chèn vào sau.\n"
                 "Cách chèn ảnh: đặt con trỏ vào dòng [CHÈN ẢNH ...] → Insert → Pictures → chọn file trong docs/images/ → xóa dòng hướng dẫn nhỏ bên dưới.")
r.italic = True
r.font.size = Pt(12)
r.font.name = FONT

doc.add_page_break()

# ================= CH1 =================
doc.add_heading("1. Giới thiệu phần mềm", level=1)
body("Phần mềm chuyển đổi văn bản thành giọng nói tự nhiên v3 biến văn bản tiếng Việt thành giọng nói, "
     "chạy hoàn toàn offline trên CPU (model đã có sẵn trong bản phát hành). "
     "Được tối ưu cho công tác phát thanh: đọc tin, đọc thông báo, xuất file âm thanh và ghép nhạc mở đầu / nền / kết thúc.")
bullet("Engine: VieNeu v3 Turbo, 48 kHz, 25 giọng preset tiếng Việt (thêm giọng tùy chỉnh nếu cần). ", "Đọc giọng AI: ")
bullet(".docx (Word) và .txt (UTF-8); có thể dán trực tiếp vào khung văn bản. ", "Hỗ trợ file: ")
bullet("Vừa tạo vừa phát, câu đang phát được tô nền vàng và tự cuộn theo. ", "Đọc streaming từng câu: ")
bullet("MP3 / WAV. Ghép nhạc: intro / nhạc nền tự lặp / outro, chỉnh volume, crossfade. ", "Xuất file: ")
bullet("Tạo giọng mới từ file mẫu âm thanh 5–30 giây, ngay trong hộp Thêm giọng mới. ", "Tạo giọng tùy chỉnh: ")
bullet("Windows 10/11 64-bit, ~1 GB RAM, loa/tai nghe. Không cần cài Python, không cần mạng. ", "Yêu cầu máy: ")

# ================= CH2 =================
doc.add_heading("2. Nhận bản phát hành v3 và khởi động lần đầu", level=1)
body("Chương này chỉ dành cho bản release v3 (file .exe portable). Bạn không cần cài Python, không chạy pip, "
     "không tải model — mọi thứ đã đóng gói sẵn.")

doc.add_heading("2.1. Nhận và giải nén bản phát hành", level=2)
bullet("Bạn sẽ nhận được 1 file nén (ZIP/RAR) bản v3. Giải nén ra một thư mục, ví dụ ", "Bước 1 – Giải nén: ")
body("D:\\VanBanGiongNoi_v3\\")
bullet("Giữ nguyên toàn bộ cấu trúc bên trong, không tách riêng file .exe, không chạy trực tiếp trong file ZIP/RAR. ",
       "Bước 2 – Giữ nguyên cấu trúc: ")
body("Cấu trúc chuẩn của bản v3:")
table(["Thành phần", "Mô tả", "Có được xóa/đổi tên?"],
      [["PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3.exe", "File chạy chính. Nháy đúp để mở app", "Không"],
       ["_internal/", "Thư viện đi kèm (do PyInstaller tạo)", "Không – xóa là app không chạy"],
       ["models/vieneu/hf_cache/", "Model giọng đọc offline (~600 MB)", "Không"],
       ["models/vieneu/custom_voices.json", "Kho giọng tùy chỉnh (giọng bạn tự tạo / được cấp)", "Không xóa; sao lưu khi chuyển máy"],
       ["models/voice_config.json", "Cấu hình: giọng nào đang được bật", "Không xóa; sao lưu khi chuyển máy"],
       ["models/test_text.json", "Câu test mặc định", "Không xóa"],
       ["HUONG_DAN_V3.txt, HUONG_DAN_SU_DUNG.docx", "Hướng dẫn sử dụng kèm theo", "Có thể xóa"]])

doc.add_heading("2.2. Khởi động lần đầu", level=2)
bullet("Mở thư mục đã giải nén → nháy đúp ", "Bước 1: ")
body("PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3.exe")
bullet("Lần đầu Windows có thể hiện SmartScreen (màn hình xanh cảnh báo vì EXE chưa ký số) → chọn “More info” → “Run anyway”. ",
       "Bước 2 – Nếu bị SmartScreen chặn: ")
bullet("Chờ vài giây để app nạp model. Thành công khi dòng trạng thái dưới thanh tiêu đề báo số giọng sẵn sàng "
       "(ví dụ 26/26 giọng) và khung văn bản trắng ở giữa đã nhập được chữ. ",
       "Bước 3 – Nhận biết chạy thành công: ")

doc.add_heading("2.3. Khác biệt bản v2 và bản v3 (để không nhầm)", level=2)
table(["Nội dung", "Bản V2", "Bản V3 (bản này)"],
      [["Code app", "Nằm rời dạng .py cạnh EXE (core/, engine/, audio/, ui/, main.py)",
        "Đóng gói hết trong EXE + _internal/ (OneDir)"],
       ["Vá lỗi nhỏ", "Chỉ cần chép đè file .py tương ứng", "Phải build lại gói mới"],
       ["Giao diện", "Sidebar trái + khung văn bản", "Thanh tiêu đề 3 hàng (logo – nguồn file – giọng đọc/test)"],
       ["Tạo giọng mới", "Chưa có", "Có tab “Tạo giọng mới” từ file mẫu âm thanh"],
       ["Model", "models/ cạnh EXE (~600 MB)", "Giống V2: models/ cạnh EXE"],
       ["Tên file EXE", "PhatThanhSo_MWDIA_V2.exe", "PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3.exe"]])

doc.add_heading("2.4. Bảo quản bản portable", level=2)
bullet("Không đổi tên/xóa thư mục _internal/ và models/. ", bold_head="Nguyên tắc 1: ")
bullet("File cấu hình (giọng được bật, câu test) lưu tại models/ cạnh EXE; giọng tùy chỉnh (.json) nhập qua "
       "Quản lý giọng đọc được lưu vào models/vieneu/custom_voices.json. Khi chuyển máy, sao lưu cả thư mục models/ "
       "để giữ nguyên cài đặt. ", bold_head="Nguyên tắc 2 – sao lưu khi chuyển máy: ")
bullet("Model offline đã nằm sẵn trong models/vieneu/hf_cache — không cần mạng, không tải thêm. "
       "Nếu phần mềm báo thiếu model, kiểm tra thư mục này còn đủ (20 file, ~600 MB). ", bold_head="Nguyên tắc 3 – offline: ")

doc.add_heading("2.5. Lỗi khởi động bản v3 thường gặp", level=2)
table(["Hiện tượng / Báo lỗi", "Nguyên nhân", "Cách xử lý"],
      [["SmartScreen chặn không cho chạy", "EXE chưa ký số", "Chọn “More info” → “Run anyway”"],
       ["Nháy đúp EXE không lên / tắt ngay", "Thiếu thư mục _internal/ cạnh EXE", "Giải nén lại đầy đủ; không tách riêng EXE"],
       ["Báo không tìm thấy mô hình", "Thiếu models/vieneu/hf_cache", "Chép lại thư mục models/ từ bản phát hành (~600 MB)"],
       ["Chạy thẳng trong file ZIP", "Chưa giải nén", "Giải nén ra thư mục rồi mới chạy"],
       ["Antivirus xóa/chặn EXE", "Nhận diện nhầm", "Khôi phục từ cách ly, thêm thư mục app vào ngoại lệ"],
       ["Không thấy file EXE", "Nhầm tên file", "Tìm đúng tên PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3.exe"]])

# ================= CH3 =================
doc.add_heading("3. Tổng quan giao diện", level=1)
body("Cửa sổ chính rộng 1200×740 gồm: thanh tiêu đề 3 hàng ở trên, khung văn bản lớn ở giữa, "
     "dạng sóng âm (waveform) và thanh phát lại ở dưới cùng.")
table(["Vùng", "Thành phần", "Chức năng"],
      [["Thanh tiêu đề – cột trái", "Logo", "Nhận diện phần mềm"],
       ["Thanh tiêu đề – hàng 1", "Nút 📁 Mở file + tên file đang mở", "Chọn file .docx / .txt để nạp vào khung văn bản"],
       ["Thanh tiêu đề – hàng 1 (phải)", "Nút ⚡ Chuyển đổi, 💾 Xuất file, 🎵 Ghép nhạc", "Tạo âm thanh, lưu file, mở hộp ghép nhạc"],
       ["Thanh tiêu đề – hàng 2", "Giọng đọc (combobox) + ＋ Thêm + Tốc độ (combobox)", "Chọn giọng, chỉnh tốc độ đọc"],
       ["Thanh tiêu đề – hàng 2 (phải)", "Nút 🔊 Test + ô nhập câu test", "Nghe thử nhanh 1 câu, lưu câu test (Enter)"],
       ["Thanh tiêu đề – hàng 3", "Dòng trạng thái", "Báo sẵn sàng / đang đệm câu / lỗi – luôn đọc dòng này khi không hiểu app đang làm gì"],
       ["Khung giữa", "Textbox + highlight vàng", "Nội dung đọc; câu đang phát nền vàng, tự cuộn theo"],
       ["Dưới phải", "Waveform + PlaybackBar", "Xem dạng sóng; kéo tua, xem 00:00/tổng số, nút Câu trước / −5s / Phát–Tạm dừng / +5s / Câu sau"]])
add_placeholder(doc, "01", "hinh-01-tong-quan.png", "Tổng quan cửa sổ chính sau khi Chuyển đổi xong",
                "Hướng dẫn chụp: mở app v3, dán 5 câu mẫu, Chuyển đổi, đợi waveform hiện đầy đủ rồi chụp full cửa sổ (Win+Shift+S → Window)",
                "15cm")

# ================= CH4 =================
doc.add_heading("4. Quy trình chuẩn 6 bước (người mới chỉ cần đọc chương này)", level=1)
steps = [
    ("Bước 1 – Nạp văn bản: ", "bấm 📁 Mở file → chọn .docx/.txt, hoặc dán (Ctrl+V) trực tiếp vào khung trắng ở giữa. Kiểm tra chữ đã hiện đầy đủ."),
    ("Bước 2 – Chọn giọng: ", "ở mục Giọng đọc, mở hộp chọn (combobox) và chọn 1 giọng. Lần đầu cứ chọn giọng đầu tiên."),
    ("Bước 3 – Nghe thử (30 giây): ", "giữ câu test mặc định hoặc gõ câu của bạn vào ô nhập câu test rồi bấm 🔊 Test. Nghe thấy tiếng là giọng dùng được."),
    ("Bước 4 – Chọn tốc độ: ", "mở hộp Tốc độ, chọn 1.0x (chuẩn đọc tin) hoặc 1.25x (nhanh hơn)."),
    ("Bước 5 – Chuyển đổi: ", "bấm nút xanh ⚡ Chuyển đổi. Dòng trạng thái sẽ chạy: Đang đệm câu 1/5... → Đang phát (3/10 câu)... → Hoàn tất! 10 câu, 45,2 giây. Chờ đến khi báo Hoàn tất. Muốn hủy giữa chừng, bấm nút ⏹ Dừng (nút Chuyển đổi đổi thành nút Dừng khi đang chạy)."),
    ("Bước 6 – Nghe lại + Xuất file: ", "bấm Phát để nghe từ đầu; kéo thanh tua để kiểm tra. Ưng ý thì bấm 💾 Xuất file → chọn MP3 (nhẹ, dễ phát) hoặc WAV (chất lượng cao) → chọn nơi lưu."),
]
for b, t in steps:
    bullet(t, b)
doc.add_heading("Lưu ý bắt buộc sau khi Chuyển đổi", level=2)
bullet("Nếu sửa bất kỳ chữ nào trong khung văn bản, đổi giọng, hoặc đổi tốc độ → phải bấm Chuyển đổi lại trước khi Phát/Xuất. "
       "Nếu không, app báo Văn bản đã thay đổi – hãy chuyển đổi lại. ", bold_head="Nhớ: ")
add_placeholder(doc, "02", "hinh-02-thanh-tieu-de-hang-1.png", "Hàng 1: Mở file, tên file, 3 nút Chuyển đổi/Xuất file/Ghép nhạc",
                "Hướng dẫn chụp: crop hàng 1 của thanh tiêu đề (từ logo/nút Mở file tới hết cột nút bên phải)",
                "12cm")
add_placeholder(doc, "03", "hinh-03-thanh-tieu-de-hang-2.png", "Hàng 2: Giọng đọc, ＋Thêm, Tốc độ, Test và ô câu test",
                "Hướng dẫn chụp: crop hàng 2 của thanh tiêu đề (Giọng đọc → hết ô câu test)",
                "12cm")
add_placeholder(doc, "04", "hinh-04-dong-trang-thai.png", "Dòng trạng thái báo kết quả",
                "Hướng dẫn chụp: crop dòng trạng thái ngay dưới thanh tiêu đề",
                "12cm")

# ================= CH5 =================
doc.add_heading("5. Hướng dẫn chi tiết từng nút", level=1)
doc.add_heading("5.1. Mở file (.docx / .txt)", level=2)
body("Bấm 📁 Mở file → hộp chọn file hiện ra → chọn .docx hoặc .txt → nội dung đổ vào khung văn bản, "
     "tên file hiện ngay cạnh nút. File .txt phải lưu dạng UTF-8 (Word/Notepad lưu mặc định thường đúng). "
     "File .docx chỉ lấy chữ đoạn văn (paragraph), không lấy ảnh/bảng. Nếu báo Không mở được file, "
     "thử mở file gốc bằng Word/Notepad xem có lỗi không.")
doc.add_heading("5.2. Giọng đọc và Test giọng", level=2)
body("Hộp Giọng đọc liệt kê các giọng đang bật (dòng trạng thái báo ví dụ 26/26 giọng sẵn sàng). "
     "Gõ câu vào ô nhập câu test (nhấn Enter để lưu câu này cho lần sau), bấm 🔊 Test để nghe thử 1 câu "
     "mà không cần chuyển đổi cả bài. Nếu đổi giọng sau khi đã Chuyển đổi, dòng trạng thái sẽ nhắc "
     "Đã đổi giọng – bấm Chuyển đổi để áp dụng.")
doc.add_heading("5.3. Tốc độ (0,5x – 2,0x)", level=2)
body("7 mức: 0,5x; 0,75x; 1,0x; 1,25x; 1,5x; 1,75x; 2,0x. Đọc tin khuyến nghị 1,0x–1,25x. "
     "Nếu đổi tốc độ khi đang phát, app tự áp ngay và giữ vị trí đang nghe. Nếu đổi khi chưa phát, "
     "app báo Đã đổi tốc độ – bấm Phát để áp dụng. Không cần chạy lại model khi đổi tốc độ.")
doc.add_heading("5.4. Chuyển đổi / Dừng", level=2)
body("Nút xanh ⚡ Chuyển đổi: tạo âm thanh cho toàn bộ văn bản. Trong lúc đang chuyển đổi, nút này đổi thành "
     "nút đỏ ⏹ Dừng để hủy giữa chừng (app báo Đã tạo N câu). Khi đang Chuyển đổi/Xuất, các nút khác bị mờ đi "
     "(busy) để tránh xung đột.")
doc.add_heading("5.5. Nghe lại: textbox, waveform, playback bar", level=2)
bullet("Câu đang phát nền vàng, tự cuộn. Chỉ để đọc theo, không bấm vào để tua (muốn tua dùng thanh kéo bên dưới). ", "Textbox: ")
bullet("Hình sóng âm, càng dài càng nhiều câu. ", "Waveform: ")
bullet("Dòng trên có thời gian hiện tại 00:00, thanh kéo (kéo để tua), tổng thời lượng. Dòng dưới có 5 nút: "
       "Câu trước (nhảy về đầu câu trước), −5s (lùi 5 giây), Phát/Tạm dừng, +5s (tiến 5 giây), Câu sau. ", "PlaybackBar: ")
add_placeholder(doc, "05", "hinh-05-highlight.png", "Câu đang phát nền vàng trong textbox",
                "Hướng dẫn chụp: Chuyển đổi 1 bài 5–10 câu, bấm Phát, đợi câu vàng hiện rồi chụp vùng textbox giữa",
                "12cm")
add_placeholder(doc, "06", "hinh-06-playback-bar.png", "Thanh phát lại: seekbar + 5 nút điều khiển",
                "Hướng dẫn chụp: crop thanh dưới cùng (seekbar + dòng 5 nút)",
                "12cm")
doc.add_heading("5.6. Xuất file MP3 / WAV", level=2)
body("Điều kiện: đã Chuyển đổi xong (waveform có sóng). Bấm 💾 Xuất file → chọn đuôi .mp3 (nhẹ, gửi Zalo/mail tiện) "
     "hoặc .wav (nặng, chất lượng gốc) → chọn thư mục lưu → đợi báo Đã xuất: đường dẫn file. "
     "File vừa xuất được lưu vào lịch sử Gần đây để dùng lại ở hộp Ghép nhạc. "
     "Nếu báo Chưa có âm thanh – hãy chuyển đổi trước nghĩa là bạn quên bước Chuyển đổi.")

# ================= CH6 =================
doc.add_heading("6. Quản lý giọng đọc (nút ＋ Thêm)", level=1)
body("Bấm ＋ Thêm ở thanh tiêu đề để mở hộp Quản lý giọng đọc. Hộp này để chọn giọng nào hiện trong hộp Giọng đọc, "
     "nhập giọng .json được cấp sẵn, tạo giọng mới từ file mẫu, xuất hoặc xóa giọng tùy chỉnh.")
bullet("Danh sách checkbox, tick giọng nào thì giọng đó hiện ở hộp Giọng đọc. Nút ☑ Tất cả / □ Bỏ chọn để chọn nhanh. ",
       "Tick/bỏ tick: ")
bullet("Bấm ＋ Thêm giọng mới → tab 📥 Nhập giọng có sẵn → Chọn tệp… → chọn file .json do quản trị viên cấp → "
       "kiểm tra tên hiện ở dưới → bấm ⬇ Nhập giọng. Giọng mới tự hiện ở hộp Giọng đọc, không cần bấm Lưu mới thấy. ",
       "Nhập giọng có sẵn: ")
bullet("Trong hộp con Thêm giọng mới, chuyển sang tab 🎙 Tạo giọng mới: đặt tên giọng → Chọn mẫu… (file wav/mp3/flac "
       "dài 5–30 giây, 1 người nói rõ, ít ồn) → tick Khử nhiễu nếu thu bằng điện thoại → bấm 🎙 Tạo giọng và chờ ~10 giây. "
       "Giọng tạo xong được lưu vào models/vieneu/custom_voices.json nên dùng lại được ở máy khác. ",
       "Tạo giọng mới từ file mẫu: ")
bullet("Mỗi giọng tùy chỉnh có 2 nút nhỏ bên phải: nút mũi tên xuống để xuất ra .json (gửi cho máy khác), "
       "nút thùng rác để xóa (hỏi xác nhận trước khi xóa). ", "Xuất / xóa giọng tùy chỉnh: ")
bullet("Bấm 💾 Lưu (nút nền tối, chữ sáng) để giữ lựa chọn, bấm ✕ Huỷ để bỏ. Nếu tắt hết giọng, "
       "dòng trạng thái báo Tất cả giọng đều bị tắt – bấm ＋ Thêm để bật lại. ", "Kết thúc: ")
add_placeholder(doc, "07", "hinh-07-quan-ly-giong.png", "Hộp Quản lý giọng đọc: checklist + nút Lưu/Huỷ",
                "Hướng dẫn chụp: mở ＋Thêm, kéo hộp ra giữa màn hình, chụp full hộp (thấy rõ nút Lưu nền tối)",
                "11cm")
add_placeholder(doc, "08", "hinh-08-them-giong-moi.png", "Hộp con Thêm giọng mới: 2 tab Nhập giọng / Tạo giọng",
                "Hướng dẫn chụp: trong hộp Quản lý, bấm ＋Thêm giọng mới, chụp hộp con (2 tab)",
                "11cm")

# ================= CH7 =================
doc.add_heading("7. Ghép nhạc phát thanh (intro / nền / outro)", level=1)
body("Bấm 🎵 Ghép nhạc ở thanh tiêu đề để mở hộp Ghép nhạc. Dùng để nối nhiều đoạn đọc + thêm nhạc mở đầu, "
     "nhạc nền tự lặp, nhạc kết thúc rồi xuất 1 file hoàn chỉnh.")
doc.add_heading("7.1. Chọn file gốc (giọng đọc)", level=2)
body("Mục File gốc: bấm Chọn file gốc (hoặc ＋ Thêm đoạn) để thêm 1 hoặc nhiều file .mp3/.wav; "
     "nhiều đoạn sẽ nối theo thứ tự từ trên xuống (có nút × để xóa từng đoạn). "
     "Ô Gần đây tự động liệt kê các file vừa Xuất ở chương 5, chọn nhanh khỏi phải tìm thư mục.")
doc.add_heading("7.2. Chọn nhạc intro / nền / outro", level=2)
bullet("Mỗi track có 3 nút: nút mở file (chọn .mp3/.wav), nút Phát thử đoạn, nút × (bỏ chọn). ", "Nút từng track: ")
bullet("Kéo 2 tay cầm đỏ để chọn đoạn nhạc muốn dùng (ví dụ chỉ lấy 0–15 s của bài intro). "
       "Dòng Đoạn: ...s bên phải tự cập nhật. ", "Kéo đoạn trên SegmentTimeline: ")
bullet("Mặc định: intro 70%, nhạc nền 15%, outro 70%. Nhạc nền để 10–20% để không át giọng đọc; "
       "nhạc nền tự lặp (loop) cho bằng độ dài giọng đọc. ", "Volume: ")
bullet("Ô nhập số giây (mặc định 0,5), là độ mở dần khi chuyển đoạn (intro → giọng → outro). Để 0,5–1 s là mượt. ",
       "Crossfade: ")
doc.add_heading("7.3. Nghe thử và xuất", level=2)
bullet("Thanh 3 màu (intro xanh đậm / voice xanh lá / outro cam) + vùng mờ crossfade + dòng chữ "
       "Intro 0:00→... | Voice ... | Outro ... giúp hình dung file cuối dài bao lâu. ", "Timeline output: ")
bullet("Bấm Nghe thử để trộn nhanh và phát thử (có thanh tua + nút Stop bên dưới). "
       "Ưng ý thì bấm Ghép & Xuất file → chọn MP3/WAV → đợi báo Đã ghép thành công. ", "Xuất: ")
add_placeholder(doc, "09", "hinh-09-ghep-nhac.png", "Toàn bộ hộp Ghép nhạc",
                "Hướng dẫn chụp: mở Ghép nhạc, chọn sẵn 1 file gốc + 1 intro + 1 bg để timeline có màu rồi chụp full hộp",
                "15cm")
add_placeholder(doc, "10", "hinh-10-track-timeline.png", "1 track nhạc: timeline kéo thả + Volume + Đoạn",
                "Hướng dẫn chụp: crop 1 ô track (ví dụ Nhạc nền) lấy đủ timeline + thanh Volume",
                "12cm")
add_placeholder(doc, "11", "hinh-11-output-timeline.png", "Timeline output + Nghe thử + Ghép & Xuất",
                "Hướng dẫn chụp: crop vùng từ Timeline output xuống hết 2 nút cuối + thanh tua",
                "12cm")

# ================= CH8 =================
doc.add_heading("8. Lỗi thường gặp, mẹo phát thanh và FAQ", level=1)
doc.add_heading("8.1. Bảng lỗi thường gặp", level=2)
table(["Báo lỗi / Hiện tượng", "Nghĩa là gì", "Làm gì"],
      [["Chưa có nội dung để chuyển đổi", "Khung văn bản trống", "Mở file hoặc dán text vào trước"],
       ["Chưa có âm thanh – hãy chuyển đổi trước", "Bấm Phát/Xuất khi chưa Chuyển đổi", "Bấm Chuyển đổi, đợi Hoàn tất rồi mới Phát/Xuất"],
       ["Văn bản đã thay đổi – hãy chuyển đổi lại", "Sửa chữ sau khi đã có âm thanh", "Bấm Chuyển đổi lại"],
       ["Đã đổi giọng/tốc độ – bấm Chuyển đổi/Phát để áp dụng", "Đổi cài đặt sau khi có âm thanh", "Làm theo dòng hướng dẫn: Chuyển đổi hoặc Phát lại"],
       ["Đang đổi tốc độ / Đang chuyển đổi – thử lại sau", "App đang bận (busy)", "Đợi xong rồi thao tác tiếp, không bấm liên tục"],
       ["Tất cả giọng đều bị tắt", "Bỏ tick hết trong Quản lý giọng", "Mở ＋Thêm → Tất cả → Lưu"],
       ["Không mở được file / Định dạng không hỗ trợ", "File không phải .docx/.txt hoặc lỗi font", "Chỉ dùng .docx/.txt UTF-8; mở thử bằng Word/Notepad"],
       ["Chưa chọn file gốc (ở Ghép nhạc)", "Quên chọn đoạn đọc", "Bấm Chọn file gốc hoặc chọn từ ô Gần đây"],
       ["Lỗi khi tạo giọng mới từ file mẫu", "Thiếu model tạo giọng hoặc mẫu âm thanh không hợp lệ", "Dùng mẫu wav/mp3 5–30 giây, 1 người nói rõ; nếu báo thiếu model thì cần mạng lần đầu"]])
doc.add_heading("8.2. Mẹo phát thanh", level=2)
bullet("Đọc tin 1,0x, đọc nhanh 1,25x; đừng để 2,0x cho bản tin chính thức. ", "Tốc độ: ")
bullet("Lưu sẵn câu test đúng tên đơn vị (nhấn Enter để lưu) để test giọng nào cũng giống nhau. ", "Câu test: ")
bullet("Nhạc nền để 10–20%, crossfade 0,5–1 s; nghe thử trước khi xuất để tránh nhạc át giọng. ", "Nhạc nền: ")
bullet("Tách câu ngắn, mỗi câu 1 ý; bỏ ký tự lạ, emoji trước khi Chuyển đổi để giọng đọc tự nhiên. ", "Văn bản: ")
bullet("Đặt tên file xuất theo mẫu Ngày_TiêuĐề_Giọng (ví dụ 2026-10-21_BanTinSang_GiongA.mp3). ", "Lưu trữ: ")
bullet("Giọng tùy chỉnh tạo từ file mẫu nên để file mẫu gốc ở nơi an toàn, xuất giọng ra .json để dùng lại "
       "trên nhiều máy. ", "Giọng tùy chỉnh: ")
doc.add_heading("8.3. FAQ", level=2)
bullet("Không. Bản v3 đã kèm model offline trong models/ nên rút mạng vẫn đọc/xuất/ghép bình thường. "
       "(Riêng chức năng tạo giọng mới có thể cần mạng lần đầu nếu máy chưa có model tạo giọng.) ",
       "Hỏi: Có cần mạng không? Đáp: ")
bullet("Có. App báo lại để đảm bảo highlight + waveform khớp chữ. ", "Hỏi: Sửa 1 chữ có phải chuyển đổi cả bài? Đáp: ")
bullet("Liên hệ quản trị viên để được cấp; bạn chỉ cần Nhập ở chương 6, hoặc tự tạo từ file mẫu âm thanh. ",
       "Hỏi: File .json giọng lấy ở đâu? Đáp: ")
bullet("MP3 để phát/gửi nhẹ; WAV để lưu trữ chất lượng gốc. ", "Hỏi: Xuất MP3 hay WAV? Đáp: ")
bullet("Có. App vừa tạo vừa phát sau ~5 câu đệm; cứ để loa, câu mới tự nối tiếp. ", "Hỏi: Đang chuyển đổi có nghe được không? Đáp: ")
bullet("Có. Khi đang chuyển đổi, nút ⚡ Chuyển đổi đổi thành nút ⏹ Dừng; bấm để hủy, app báo số câu đã tạo. ",
       "Hỏi: Dừng giữa chừng được không? Đáp: ")

doc.add_page_break()
doc.add_heading("Phụ lục: Checklist 11 ảnh cần chụp", level=1)
body("Chụp bằng Win+Shift+S, lưu PNG vào docs/images/ đúng tên bên dưới, rồi trong Word: "
     "đặt con trỏ vào dòng [CHÈN ẢNH ...] → Insert → Pictures → chọn file → xóa dòng hướng dẫn nhỏ. "
     "Cột cuối để bạn tick tay sau khi in (Chưa/Chèn xong).")
table(["Mã", "Tên file", "Chụp gì / Cỡ hiển thị"],
      [["01", "hinh-01-tong-quan.png", "Full cửa sổ sau Chuyển đổi / 15cm"],
       ["02", "hinh-02-thanh-tieu-de-hang-1.png", "Hàng 1 thanh tiêu đề / 12cm"],
       ["03", "hinh-03-thanh-tieu-de-hang-2.png", "Hàng 2 thanh tiêu đề / 12cm"],
       ["04", "hinh-04-dong-trang-thai.png", "Dòng trạng thái / 12cm"],
       ["05", "hinh-05-highlight.png", "Câu nền vàng / 12cm"],
       ["06", "hinh-06-playback-bar.png", "Seekbar + 5 nút / 12cm"],
       ["07", "hinh-07-quan-ly-giong.png", "Hộp Quản lý giọng / 11cm"],
       ["08", "hinh-08-them-giong-moi.png", "Hộp Thêm giọng mới (2 tab) / 11cm"],
       ["09", "hinh-09-ghep-nhac.png", "Full hộp Ghép nhạc / 15cm"],
       ["10", "hinh-10-track-timeline.png", "1 track + Volume / 12cm"],
       ["11", "hinh-11-output-timeline.png", "Timeline output + Xuất / 12cm"]])

body("Thông tin tài liệu: Phần mềm chuyển đổi văn bản thành giọng nói tự nhiên v3, phiên bản 3.0.0 "
     "(bản phát hành OneDir: EXE + _internal/ + models/ cạnh nhau). "
     "Tài liệu này thay thế mọi hướng dẫn miệng trước đây; khi app lên phiên bản mới, "
     "chỉ cần chụp lại các ảnh có giao diện thay đổi.")

# Ép font trực tiếp cho mọi run kế thừa style (heading, bullet) để Word luôn hiện Times New Roman
for _p in doc.paragraphs:
    for _r in _p.runs:
        if _r.font.name is None:
            _r.font.name = FONT
        try:
            _r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
            _r._element.rPr.rFonts.set(qn("w:cs"), FONT)
        except Exception:
            pass
for _t in doc.tables:
    for _row in _t.rows:
        for _c in _row.cells:
            for _p in _c.paragraphs:
                for _r in _p.runs:
                    if _r.font.name is None:
                        _r.font.name = FONT

try:
    doc.save(OUT)
except PermissionError:
    OUT2 = OUT.replace(".docx", "_moi.docx")
    doc.save(OUT2)
    OUT = OUT2
print(f"[OK] Da sinh {OUT}")
