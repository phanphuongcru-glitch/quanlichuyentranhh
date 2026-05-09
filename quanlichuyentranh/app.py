"""
╔══════════════════════════════════════════════╗
║       TIỆM TRUYỆN CŨ - Quản lý cửa hàng    ║
║       Bán & Cho thuê truyện tranh            ║
║       Python Flask + Desktop App (webview)   ║
╚══════════════════════════════════════════════╝
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import json
import os
import sys
import hashlib
import threading
from datetime import datetime, timedelta

# ─── Xác định đường dẫn (hỗ trợ cả .py và .exe) ───
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    TEMPLATE_DIR = os.path.join(sys._MEIPASS, 'templates')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = "tiem_truyen_cu_secret_key_2024"

DB_FILE = os.path.join(BASE_DIR, "data.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")


# ═══════════════════════════════════════
# AUTH HELPERS
# ═══════════════════════════════════════

def hash_pw(pw):
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_users()

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_default_users():
    return {
        "users": [
            {"id": 1, "username": "admin", "password": hash_pw("admin123"),
             "fullname": "Quản trị viên", "role": "admin", "created": "01/01/2024"},
            {"id": 2, "username": "nhanvien", "password": hash_pw("nv123"),
             "fullname": "Nhân viên A", "role": "staff", "created": "01/01/2024"},
        ],
        "next_id": 3,
    }

def current_user():
    if "user_id" not in session:
        return None
    users = load_users()
    return next((u for u in users["users"] if u["id"] == session["user_id"]), None)

def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập!", "error")
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        u = current_user()
        if not u or u["role"] != "admin":
            flash("Bạn không có quyền thực hiện!", "error")
            return redirect(url_for("home"))
        return f(*a, **kw)
    return wrap


# ═══════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            flash("Nhập đầy đủ tên đăng nhập và mật khẩu!", "error")
            return render_template("login.html", page="login", username=username)
        users = load_users()
        user = next((u for u in users["users"]
                      if u["username"] == username and u["password"] == hash_pw(password)), None)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["fullname"] = user["fullname"]
            session["role"] = user["role"]
            flash(f'Xin chào, {user["fullname"]}! 👋', "success")
            return redirect(url_for("home"))
        else:
            flash("Sai tên đăng nhập hoặc mật khẩu!", "error")
            return render_template("login.html", page="login", username=username)
    return render_template("login.html", page="login")

@app.route("/register", methods=["GET", "POST"])
def register():
    user = current_user()
    if user and user["role"] != "admin":
        flash("Chỉ admin mới được tạo tài khoản!", "error")
        return redirect(url_for("home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        password2 = request.form.get("password2", "").strip()
        fullname = request.form.get("fullname", "").strip()
        role = request.form.get("role", "staff")
        if not username or not password or not fullname:
            flash("Nhập đầy đủ thông tin!", "error")
            return render_template("login.html", page="register", username=username, fullname=fullname)
        if len(username) < 3:
            flash("Tên đăng nhập tối thiểu 3 ký tự!", "error")
            return render_template("login.html", page="register", username=username, fullname=fullname)
        if len(password) < 4:
            flash("Mật khẩu tối thiểu 4 ký tự!", "error")
            return render_template("login.html", page="register", username=username, fullname=fullname)
        if password != password2:
            flash("Mật khẩu nhập lại không khớp!", "error")
            return render_template("login.html", page="register", username=username, fullname=fullname)
        users = load_users()
        if any(u["username"] == username for u in users["users"]):
            flash("Tên đăng nhập đã tồn tại!", "error")
            return render_template("login.html", page="register", username=username, fullname=fullname)
        if not user or user["role"] != "admin":
            role = "staff"
        new_user = {
            "id": users["next_id"], "username": username, "password": hash_pw(password),
            "fullname": fullname, "role": role, "created": datetime.now().strftime("%d/%m/%Y"),
        }
        users["next_id"] += 1
        users["users"].append(new_user)
        save_users(users)
        flash(f'Tạo tài khoản "{username}" thành công! Hãy đăng nhập.', "success")
        return redirect(url_for("login"))
    return render_template("login.html", page="register", is_admin=(user and user["role"] == "admin"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất!", "success")
    return redirect(url_for("login"))

@app.route("/profile")
@login_required
def profile():
    user = current_user()
    all_users = load_users()["users"] if user["role"] == "admin" else None
    return render_template("index.html", page="profile", user=user, all_users=all_users)

@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    old_pw = request.form.get("old_password", "").strip()
    new_pw = request.form.get("new_password", "").strip()
    new_pw2 = request.form.get("new_password2", "").strip()
    users = load_users()
    user = next((u for u in users["users"] if u["id"] == session["user_id"]), None)
    if not user or user["password"] != hash_pw(old_pw):
        flash("Mật khẩu cũ không đúng!", "error")
        return redirect(url_for("profile"))
    if len(new_pw) < 4:
        flash("Mật khẩu mới tối thiểu 4 ký tự!", "error")
        return redirect(url_for("profile"))
    if new_pw != new_pw2:
        flash("Mật khẩu mới nhập lại không khớp!", "error")
        return redirect(url_for("profile"))
    user["password"] = hash_pw(new_pw)
    save_users(users)
    flash("Đã đổi mật khẩu thành công!", "success")
    return redirect(url_for("profile"))

@app.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    if user_id == session["user_id"]:
        flash("Không thể xóa chính mình!", "error")
        return redirect(url_for("profile"))
    users = load_users()
    target = next((u for u in users["users"] if u["id"] == user_id), None)
    if target:
        users["users"] = [u for u in users["users"] if u["id"] != user_id]
        save_users(users)
        flash(f'Đã xóa tài khoản "{target["username"]}"', "success")
    return redirect(url_for("profile"))


# ═══════════════════════════════════════
# DATA HELPERS
# ═══════════════════════════════════════

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return get_default_data()

def save_data(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_default_data():
    return {
        "books": [
            {"id": 1, "title": "Doraemon - Tập 1", "author": "Fujiko F. Fujio", "genre": "Manga", "price": 25000, "rental_price": 5000, "stock": 12, "emoji": "📘"},
            {"id": 2, "title": "Conan - Tập 45", "author": "Aoyama Gosho", "genre": "Manga", "price": 28000, "rental_price": 6000, "stock": 8, "emoji": "🔍"},
            {"id": 3, "title": "Dragon Ball - Tập 10", "author": "Toriyama Akira", "genre": "Manga", "price": 30000, "rental_price": 5000, "stock": 5, "emoji": "🐉"},
            {"id": 4, "title": "Naruto - Tập 72", "author": "Kishimoto Masashi", "genre": "Manga", "price": 32000, "rental_price": 7000, "stock": 3, "emoji": "🍥"},
            {"id": 5, "title": "One Piece - Tập 100", "author": "Oda Eiichiro", "genre": "Manga", "price": 35000, "rental_price": 8000, "stock": 10, "emoji": "🏴‍☠️"},
            {"id": 6, "title": "Shin - Cậu bé bút chì", "author": "Usui Yoshito", "genre": "Manga", "price": 22000, "rental_price": 4000, "stock": 15, "emoji": "✏️"},
            {"id": 7, "title": "Tôi thấy hoa vàng trên cỏ xanh", "author": "Nguyễn Nhật Ánh", "genre": "Văn học VN", "price": 68000, "rental_price": 10000, "stock": 6, "emoji": "🌻"},
            {"id": 8, "title": "Mắt biếc", "author": "Nguyễn Nhật Ánh", "genre": "Văn học VN", "price": 72000, "rental_price": 12000, "stock": 4, "emoji": "👁️"},
        ],
        "sales": [], "rentals": [],
        "customers": [
            {"id": 1, "name": "Nguyễn Văn An", "phone": "0901234567", "address": "Hoàn Kiếm, Hà Nội"},
            {"id": 2, "name": "Trần Thị Bình", "phone": "0912345678", "address": "Quận 1, HCM"},
            {"id": 3, "name": "Lê Minh Châu", "phone": "0923456789", "address": "Hải Châu, Đà Nẵng"},
        ],
        "next_ids": {"book": 9, "sale": 1, "rental": 1, "customer": 4}
    }

def fmt_money(n):
    return f"{n:,.0f}đ".replace(",", ".")

def now_str():
    return datetime.now().strftime("%d/%m/%Y %H:%M")

app.jinja_env.filters["money"] = fmt_money


# ═══════════════════════════════════════
# MAIN ROUTES
# ═══════════════════════════════════════

@app.route("/")
@login_required
def home():
    data = load_data()
    stats = {
        "total_titles": len(data["books"]),
        "total_stock": sum(b["stock"] for b in data["books"]),
        "sale_revenue": sum(s["total"] for s in data["sales"]),
        "sale_count": len(data["sales"]),
        "rental_revenue": sum(r["total"] for r in data["rentals"]),
        "active_rentals": len([r for r in data["rentals"] if not r["returned"]]),
        "total_customers": len(data["customers"]),
    }
    recent_sales = list(reversed(data["sales"][-5:]))
    active_rentals = [r for r in data["rentals"] if not r["returned"]][-5:]
    active_rentals.reverse()
    return render_template("index.html", page="home", stats=stats,
                           recent_sales=recent_sales, active_rentals=active_rentals)

@app.route("/books")
@login_required
def books():
    data = load_data()
    q = request.args.get("q", "").lower()
    genre = request.args.get("genre", "")
    filtered = data["books"]
    if q: filtered = [b for b in filtered if q in b["title"].lower() or q in b["author"].lower()]
    if genre: filtered = [b for b in filtered if b["genre"] == genre]
    genres = sorted(set(b["genre"] for b in data["books"]))
    return render_template("index.html", page="books", books=filtered, genres=genres, q=q, genre_filter=genre)

@app.route("/books/add", methods=["POST"])
@login_required
def add_book():
    data = load_data()
    book = {"id": data["next_ids"]["book"], "title": request.form["title"].strip(),
            "author": request.form["author"].strip(), "genre": request.form["genre"].strip() or "Manga",
            "price": int(request.form.get("price", 25000)), "rental_price": int(request.form.get("rental_price", 5000)),
            "stock": int(request.form.get("stock", 10)), "emoji": request.form.get("emoji", "📘")}
    data["next_ids"]["book"] += 1
    data["books"].append(book)
    save_data(data)
    flash(f'Đã thêm "{book["title"]}"', "success")
    return redirect(url_for("books"))

@app.route("/books/edit/<int:book_id>", methods=["POST"])
@login_required
def edit_book(book_id):
    data = load_data()
    for b in data["books"]:
        if b["id"] == book_id:
            b.update({"title": request.form["title"].strip(), "author": request.form["author"].strip(),
                       "genre": request.form["genre"].strip(), "price": int(request.form.get("price", b["price"])),
                       "rental_price": int(request.form.get("rental_price", b["rental_price"])),
                       "stock": int(request.form.get("stock", b["stock"])), "emoji": request.form.get("emoji", b["emoji"])})
            flash(f'Đã cập nhật "{b["title"]}"', "success"); break
    save_data(data)
    return redirect(url_for("books"))

@app.route("/books/delete/<int:book_id>", methods=["POST"])
@login_required
@admin_required
def delete_book(book_id):
    data = load_data()
    book = next((b for b in data["books"] if b["id"] == book_id), None)
    if book:
        data["books"] = [b for b in data["books"] if b["id"] != book_id]
        save_data(data)
        flash(f'Đã xóa "{book["title"]}"', "success")
    return redirect(url_for("books"))

@app.route("/sales")
@login_required
def sales():
    data = load_data()
    q = request.args.get("q", "").lower()
    sale_list = list(reversed(data["sales"]))
    if q: sale_list = [s for s in sale_list if q in s["title"].lower() or q in s["customer"].lower()]
    return render_template("index.html", page="sales", sales=sale_list,
                           books=[b for b in data["books"] if b["stock"] > 0], customers=data["customers"], q=q)

@app.route("/sales/add", methods=["POST"])
@login_required
def add_sale():
    data = load_data()
    book_id = int(request.form["book_id"]); qty = int(request.form.get("qty", 1))
    customer = request.form["customer"].strip()
    book = next((b for b in data["books"] if b["id"] == book_id), None)
    if not book: flash("Không tìm thấy truyện!", "error"); return redirect(url_for("sales"))
    if book["stock"] < qty: flash("Không đủ hàng!", "error"); return redirect(url_for("sales"))
    if not customer: flash("Nhập tên khách!", "error"); return redirect(url_for("sales"))
    book["stock"] -= qty
    sale = {"id": data["next_ids"]["sale"], "book_id": book_id, "title": book["title"], "qty": qty,
            "price": book["price"], "total": book["price"] * qty, "customer": customer,
            "seller": session.get("fullname", ""), "date": now_str()}
    data["next_ids"]["sale"] += 1; data["sales"].append(sale); save_data(data)
    flash(f'Bán {qty}x "{book["title"]}" cho {customer} — {fmt_money(sale["total"])}', "success")
    return redirect(url_for("sales"))

@app.route("/rentals")
@login_required
def rentals():
    data = load_data()
    view = request.args.get("view", "active"); q = request.args.get("q", "").lower()
    rl = [r for r in data["rentals"] if not r["returned"]] if view == "active" else data["rentals"]
    rl = list(reversed(rl))
    if q: rl = [r for r in rl if q in r["title"].lower() or q in r["customer"].lower()]
    return render_template("index.html", page="rentals", rentals=rl,
                           books=[b for b in data["books"] if b["stock"] > 0], customers=data["customers"], view=view, q=q)

@app.route("/rentals/add", methods=["POST"])
@login_required
def add_rental():
    data = load_data()
    book_id = int(request.form["book_id"]); customer = request.form["customer"].strip()
    days = int(request.form.get("days", 3))
    book = next((b for b in data["books"] if b["id"] == book_id), None)
    if not book: flash("Không tìm thấy!", "error"); return redirect(url_for("rentals"))
    if book["stock"] < 1: flash("Hết hàng!", "error"); return redirect(url_for("rentals"))
    if not customer: flash("Nhập tên khách!", "error"); return redirect(url_for("rentals"))
    book["stock"] -= 1
    due = datetime.now() + timedelta(days=days)
    rental = {"id": data["next_ids"]["rental"], "book_id": book_id, "title": book["title"],
              "customer": customer, "rate": book["rental_price"], "days": days,
              "total": book["rental_price"] * days, "date": now_str(), "due": due.strftime("%d/%m/%Y"),
              "returned": False, "return_date": None, "staff": session.get("fullname", "")}
    data["next_ids"]["rental"] += 1; data["rentals"].append(rental); save_data(data)
    flash(f'Cho thuê "{book["title"]}" → {customer} ({days} ngày)', "success")
    return redirect(url_for("rentals"))

@app.route("/rentals/return/<int:rental_id>", methods=["POST"])
@login_required
def return_rental(rental_id):
    data = load_data()
    r = next((r for r in data["rentals"] if r["id"] == rental_id), None)
    if r and not r["returned"]:
        r["returned"] = True; r["return_date"] = now_str()
        book = next((b for b in data["books"] if b["id"] == r["book_id"]), None)
        if book: book["stock"] += 1
        save_data(data)
        flash(f'Nhận trả "{r["title"]}" từ {r["customer"]}', "success")
    return redirect(url_for("rentals"))

@app.route("/customers")
@login_required
def customers():
    data = load_data()
    q = request.args.get("q", "").lower()
    filtered = data["customers"]
    if q: filtered = [c for c in filtered if q in c["name"].lower() or q in c.get("phone", "")]
    for c in filtered:
        buys = [s for s in data["sales"] if s["customer"] == c["name"]]
        rents = [r for r in data["rentals"] if r["customer"] == c["name"]]
        c["buy_count"] = len(buys); c["rent_count"] = len(rents)
        c["total_spent"] = sum(s["total"] for s in buys) + sum(r["total"] for r in rents)
    return render_template("index.html", page="customers", customers=filtered, q=q)

@app.route("/customers/add", methods=["POST"])
@login_required
def add_customer():
    data = load_data()
    cust = {"id": data["next_ids"]["customer"], "name": request.form["name"].strip(),
            "phone": request.form.get("phone", "").strip(), "address": request.form.get("address", "").strip()}
    if not cust["name"]: flash("Nhập tên!", "error"); return redirect(url_for("customers"))
    data["next_ids"]["customer"] += 1; data["customers"].append(cust); save_data(data)
    flash(f'Đã thêm "{cust["name"]}"', "success")
    return redirect(url_for("customers"))

@app.route("/reports")
@login_required
def reports():
    data = load_data()
    stats = {"sale_revenue": sum(s["total"] for s in data["sales"]), "sale_count": len(data["sales"]),
             "rental_revenue": sum(r["total"] for r in data["rentals"]), "rental_count": len(data["rentals"])}
    stats["total_revenue"] = stats["sale_revenue"] + stats["rental_revenue"]
    sm = {}
    for s in data["sales"]: sm[s["title"]] = sm.get(s["title"], 0) + s["qty"]
    top_sold = sorted(sm.items(), key=lambda x: -x[1])[:5]
    rm = {}
    for r in data["rentals"]: rm[r["title"]] = rm.get(r["title"], 0) + 1
    top_rented = sorted(rm.items(), key=lambda x: -x[1])[:5]
    low_stock = sorted([b for b in data["books"] if b["stock"] <= 3], key=lambda x: x["stock"])
    return render_template("index.html", page="reports", stats=stats,
                           top_sold=top_sold, top_rented=top_rented, low_stock=low_stock)

@app.route("/reset", methods=["POST"])
@login_required
@admin_required
def reset_data():
    save_data(get_default_data())
    flash("Đã khôi phục dữ liệu gốc!", "success")
    return redirect(url_for("home"))


# ═══════════════════════════════════════
# KHỞI CHẠY - Desktop App
# ═══════════════════════════════════════

def start_flask():
    """Chạy Flask server ở background"""
    if not os.path.exists(DB_FILE):
        save_data(get_default_data())
    if not os.path.exists(USERS_FILE):
        save_users(get_default_users())
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Kiểm tra có webview không
    try:
        import webview

        # Chạy Flask trong thread riêng
        flask_thread = threading.Thread(target=start_flask, daemon=True)
        flask_thread.start()

        # Đợi Flask khởi động
        import time
        time.sleep(1.5)

        # Mở cửa sổ app
        window = webview.create_window(
            title="📚 Tiệm Truyện Cũ - Quản lý cửa hàng",
            url="http://127.0.0.1:5000",
            width=1200,
            height=800,
            resizable=True,
            min_size=(900, 600),
        )
        webview.start()

    except ImportError:
        # Không có webview → chạy bằng trình duyệt
        import webbrowser
        print("=" * 50)
        print("  TIEM TRUYEN CU - Quan ly cua hang")
        print("  Dang mo trinh duyet...")
        print("  Tai khoan mac dinh:")
        print("     Admin:     admin / admin123")
        print("     Nhan vien: nhanvien / nv123")
        print("=" * 50)

        if not os.path.exists(DB_FILE):
            save_data(get_default_data())
        if not os.path.exists(USERS_FILE):
            save_users(get_default_users())

        # Tự mở trình duyệt
        threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
        app.run(host="127.0.0.1", port=5000, debug=False)