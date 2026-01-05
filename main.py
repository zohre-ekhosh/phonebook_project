import flet as ft
import csv
from io import StringIO
import os
import base64
import uuid
import shutil
import re
from database import PhoneBookDB


class ContactRow(ft.Container):
    def __init__(self, contact, is_admin=False, on_edit=None, on_delete=None):
        super().__init__()
        self.contact = contact
        self.is_admin = is_admin
        self.on_edit_callback = on_edit
        self.on_delete_callback = on_delete
        self.build()

    def build(self):
        photo_display = self.create_photo_display()
        
        cells = [
            ft.Container(ft.Text(str(self.contact.get("id", "")), size=12), width=50, padding=5),
            ft.Container(photo_display, width=80, padding=5, alignment=ft.alignment.center),
            ft.Container(ft.Text(self.contact.get("first_name", ""), size=12), width=100, padding=5),
            ft.Container(ft.Text(self.contact.get("last_name", ""), size=12), width=100, padding=5),
            ft.Container(ft.Text(self.contact.get("group_name", ""), size=12), width=100, padding=5),
            ft.Container(ft.Text(self.contact.get("position", "") if self.contact.get("position") else "-", size=12), width=100, padding=5),
            ft.Container(ft.Text(self.contact.get("email", "") if self.contact.get("email") else "-", size=12), width=130, padding=5),
            ft.Container(ft.Text(self.contact.get("phone", ""), size=12), width=100, padding=5),
        ]

        if self.is_admin:
            edit_button = ft.IconButton(
                icon=ft.Icons.EDIT,
                icon_color="orange",
                on_click=lambda e, cid=self.contact["id"]: self.on_edit_callback(cid) if self.on_edit_callback else None,
                icon_size=16,
                tooltip="ویرایش",
            )
            
            delete_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                icon_color="red",
                on_click=lambda e, cid=self.contact["id"]: self.on_delete_callback(cid) if self.on_delete_callback else None,
                icon_size=16,
                tooltip="حذف",
            )
            
            actions = ft.Row([edit_button, delete_button], spacing=5)
            cells.append(ft.Container(actions, width=100, padding=5))

        self.content = ft.Row(cells, spacing=0)
        self.padding = ft.padding.all(8)
        self.bgcolor = ft.Colors.WHITE
        self.border_radius = 5
        self.border = ft.border.all(0.5, ft.Colors.GREY_300)
        self.margin = ft.margin.only(bottom=5)

    def create_photo_display(self):
        # Display contact photo or default avatar
        photo_path = self.contact.get("photo_path")
        
        if photo_path and os.path.exists(photo_path):
            try:
                with open(photo_path, 'rb') as f:
                    image_bytes = f.read()
                    base64_image = base64.b64encode(image_bytes).decode()
                
                return ft.Image(
                    src_base64=base64_image,
                    width=60,
                    height=60,
                    fit=ft.ImageFit.COVER,
                    border_radius=30,
                )
            except:
                pass
        
        return ft.Container(
            content=ft.Icon(
                name=ft.Icons.PERSON,
                color=ft.Colors.GREY_400,
                size=40,
            ),
            width=60,
            height=60,
            border_radius=30,
            bgcolor=ft.Colors.GREY_200,
            alignment=ft.alignment.center,
        )


class PhoneBookApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.db = PhoneBookDB("phonebook.db")
        self.is_admin = False
        
        self.photos_dir = "contact_photos"
        os.makedirs(self.photos_dir, exist_ok=True)
        
        self.logo_path = "assets/111.png"
        
        self.search_fields = {
            "first_name": ft.TextField(label="نام", width=150, border_color=ft.Colors.ORANGE_400),
            "last_name": ft.TextField(label="نام خانوادگی", width=160, border_color=ft.Colors.ORANGE_400),
            "group_name": ft.TextField(label="گروه آموزشی", width=150, border_color=ft.Colors.ORANGE_400),
            "position": ft.TextField(label="سمت اجرایی", width=150, border_color=ft.Colors.ORANGE_400),
            "email": ft.TextField(label="ایمیل", width=180, border_color=ft.Colors.ORANGE_400),
            "phone": ft.TextField(label="تلفن", width=160, border_color=ft.Colors.ORANGE_400)
        }
        
        for field in self.search_fields.values():
            field.on_submit = self.handle_search_enter
        
        self.contacts_container = ft.Column(spacing=0, scroll="auto")
        self.current_dialog = None
        
        self.setup_page()
        self.build_ui()
        self.load_contacts()
    
    def validate_phone(self, phone):
        # Validate Iranian phone numbers
        if not phone or not str(phone).strip():
            return False, "شماره تلفن نمی‌تواند خالی باشد"
        
        cleaned = re.sub(r'[^\d+]', '', str(phone))
        
        # Valid Iranian phone patterns
        patterns = [
            r'^\+98\d{10}$',      # +989121234567
            r'^0098\d{10}$',      # 00989121234567
            r'^98\d{10}$',        # 989121234567
            r'^09\d{9}$',         # 09121234567
            r'^9\d{9}$',          # 9121234567
            r'^\d{10}$',          # 09121234567 یا 0211234567
            r'^0\d{10}$',         # 02112345678
            r'^0\d{2,9}$',        # Other landlines
        ]
        
        for pattern in patterns:
            if re.match(pattern, cleaned):
                return True, self.format_phone(cleaned)
        
        return False, "شماره تلفن نامعتبر است. فرمت‌های قابل قبول: 09123456789 یا 02187654321"
    
    def format_phone(self, phone):
        # Standardize phone format
        cleaned = re.sub(r'[^\d+]', '', str(phone))
        
        # Convert +98 to 0
        if cleaned.startswith('+98'):
            if cleaned.startswith('+989'):
                return f"0{cleaned[3:]}"
            return cleaned[1:]
        
        # Convert 0098 to 0
        if cleaned.startswith('0098'):
            if cleaned.startswith('00989'):
                return f"0{cleaned[4:]}"
            return cleaned[2:]
        
        # Convert 98 to 0
        if cleaned.startswith('98'):
            if cleaned.startswith('989'):
                return f"0{cleaned[2:]}"
            return cleaned
        
        # Add leading 0 to mobile numbers
        if cleaned.startswith('9') and len(cleaned) == 10:
            return f"0{cleaned}"
        
        # Add leading 0 to 10-digit numbers
        if not cleaned.startswith('0') and len(cleaned) == 10:
            return f"0{cleaned}"
        
        return cleaned
    
    def show_validation_error(self, message):
        # Show error snackbar
        self.page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.ERROR, color=ft.Colors.WHITE),
                ft.Text(message, color=ft.Colors.WHITE, size=14),
            ]),
            bgcolor=ft.Colors.RED_400,
            duration=3000,
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def show_success_message(self, message):
        # Show success snackbar
        self.page.snack_bar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.WHITE),
                ft.Text(message, color=ft.Colors.WHITE, size=14),
            ]),
            bgcolor=ft.Colors.GREEN_400,
            duration=3000,
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def handle_search_enter(self, e):
        # Load contacts on Enter key
        self.load_contacts()

    def setup_page(self):
        # Configure page settings
        self.page.title = "سامانه مدیریت اطلاعات تماس"
        self.page.rtl = True
        self.page.bgcolor = ft.Colors.GREY_100
        self.page.padding = 25
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.scroll = "auto"
        self.page.window_width = 1300
        self.page.window_height = 850

    def build_header(self):
        # Build header with logo and role toggle
        logo_widget = self.get_logo_widget()
        
        return ft.Container(
            padding=20,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row([
                        logo_widget,
                        ft.Text("سامانه مدیریت \nاطلاعات تماس", 
                            size=15, 
                            weight=ft.FontWeight.BOLD, 
                            color=ft.Colors.ORANGE_600),
                    ]),
                    ft.Row(
                        spacing=15,
                        controls=[
                            ft.Container(
                                content=ft.Row([
                                    ft.Icon(
                                        name=ft.Icons.ADMIN_PANEL_SETTINGS if self.is_admin else ft.Icons.PERSON,
                                        color=ft.Colors.ORANGE_700,
                                    ),
                                    ft.Text(
                                        "مدیر سیستم" if self.is_admin else "کاربر عادی",
                                        size=12,
                                        color=ft.Colors.ORANGE_800
                                    ),
                                ]),
                                padding=10,
                                border_radius=10,
                                bgcolor=ft.Colors.ORANGE_100,
                            ),
                            ft.Switch(
                                value=self.is_admin,
                                label="تغییر نقش",
                                active_color=ft.Colors.ORANGE_400,
                                on_change=self.toggle_role,
                            ),
                        ],
                    ),
                ],
            ),
        )
    
    def get_logo_widget(self):
        # Load logo from possible paths
        possible_paths = [
            "assets/111.png",
            "111.png",
            "./assets/111.png",
        ]
        
        for logo_path in possible_paths:
            if os.path.exists(logo_path):
                try:
                    with open(logo_path, 'rb') as f:
                        image_bytes = f.read()
                        base64_image = base64.b64encode(image_bytes).decode()
                    
                    return ft.Image(
                        src_base64=base64_image,
                        width=48,
                        height=48,
                        fit=ft.ImageFit.CONTAIN,
                    )
                except Exception:
                    continue
        
        return ft.Icon(
            name=ft.Icons.CONTACTS,
            size=48,
            color=ft.Colors.ORANGE_600,
        )

    def hero_title(self, text="سامانه مدیریت اطلاعات تماس", size=28):
        # Create main title section
        return ft.Container(
            width=self.page.width,
            padding=20,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.only(bottom=ft.BorderSide(1.5, ft.Colors.ORANGE_200)),
            content=ft.Text(
                text,
                size=size,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.RIGHT,
                color=ft.Colors.ORANGE_800,
            )
        )

    def build_search_box(self):
        # Create advanced search form
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            padding=20,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.GREY_300),
            shadow=ft.BoxShadow(blur_radius=2, color=ft.Colors.BLACK12),
            content=ft.Column(
                spacing=20,
                controls=[
                    ft.Text("جستجوی پیشرفته", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_800),
                    ft.Row(
                        [
                            ft.Container(
                                content=self.search_fields["first_name"],
                                expand=True,
                            ),
                            ft.Container(
                                content=self.search_fields["last_name"],
                                expand=True,
                            ),
                            ft.Container(
                                content=self.search_fields["group_name"],
                                expand=True,
                            ),
                            ft.Container(
                                content=self.search_fields["position"],
                                expand=True,
                            ),
                            ft.Container(
                                content=self.search_fields["email"],
                                expand=True,
                            ),
                            ft.Container(
                                content=self.search_fields["phone"],
                                expand=True,
                            ),
                        ],
                        wrap=False,
                        spacing=15,
                    ),
                ]
            ),
        )

    def build_admin_actions(self):
        # Show admin buttons if admin mode
        if not self.is_admin:
            return ft.Container()
        
        add_button = ft.ElevatedButton(
            "افزودن مخاطب",
            icon=ft.Icons.PERSON_ADD,
            bgcolor=ft.Colors.ORANGE_400,
            color=ft.Colors.WHITE,
            on_click=self.show_add_dialog,
            style=ft.ButtonStyle(padding=15),
        )
        
        add_csv_button = ft.ElevatedButton(
            "افزودن از CSV",
            icon=ft.Icons.UPLOAD_FILE,
            bgcolor="#F2C03E",
            color=ft.Colors.WHITE,
            on_click=self.show_add_csv_dialog,
            style=ft.ButtonStyle(padding=15),
        )
        
        return ft.Container(
            bgcolor=ft.Colors.WHITE,
            padding=15,
            border_radius=12,
            border=ft.border.all(1, ft.Colors.GREY_300),
            content=ft.Row(
                spacing=15,
                controls=[
                    add_button,
                    add_csv_button,
                ],
            ),
        )

    def create_table_header(self):
        # Create table header row
        headers = ["#", "عکس", "نام", "نام خانوادگی", "گروه آموزشی", "سمت اجرایی", "ایمیل", "تلفن"]
        if self.is_admin:
            headers.append("عملیات")
        
        header_cells = []
        widths = [50, 80, 100, 100, 100, 100, 130, 100, 100] if self.is_admin else [50, 80, 100, 100, 100, 100, 130, 100]
        
        for i, header in enumerate(headers):
            header_cells.append(
                ft.Container(
                    ft.Text(header, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_800, size=12),
                    width=widths[i] if i < len(widths) else 100,
                    padding=10,
                    bgcolor=ft.Colors.ORANGE_50,
                    border_radius=5,
                    alignment=ft.alignment.center,
                )
            )
        
        return ft.Container(
            ft.Row(header_cells, spacing=0),
            padding=ft.padding.only(bottom=10),
        )

    def load_contacts(self, e=None):
        # Load and display contacts
        self.contacts_container.controls.clear()
        self.contacts_container.controls.append(self.create_table_header())
        
        filters = {key: field.value for key, field in self.search_fields.items()}
        contacts = self.db.search(filters)
        
        if not contacts:
            empty_row = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Text("هیچ مخاطبی یافت نشد", color=ft.Colors.GREY_500, italic=True, size=12),
                        padding=20,
                        alignment=ft.alignment.center,
                        expand=True,
                    )
                ]),
                bgcolor=ft.Colors.WHITE,
                border_radius=5,
                padding=10,
                margin=ft.margin.only(bottom=5),
            )
            self.contacts_container.controls.append(empty_row)
        else:
            for contact in contacts:
                row = ContactRow(
                    contact=contact,
                    is_admin=self.is_admin,
                    on_edit=self.edit_contact,
                    on_delete=self.delete_contact
                )
                self.contacts_container.controls.append(row)
        
        self.page.update()

    def toggle_role(self, e):
        # Switch between admin and user roles
        self.is_admin = e.control.value
        self.page.controls.clear()
        self.build_ui()
        self.load_contacts()
        self.page.update()

    def clear_search(self, e):
        # Clear search fields
        for field in self.search_fields.values():
            field.value = ""
        self.load_contacts()

    def create_photo_preview(self, photo_path):
        # Create photo preview widget
        if photo_path and os.path.exists(photo_path):
            try:
                with open(photo_path, 'rb') as f:
                    image_bytes = f.read()
                    base64_image = base64.b64encode(image_bytes).decode()
                
                return ft.Image(
                    src_base64=base64_image,
                    width=120,
                    height=120,
                    fit=ft.ImageFit.COVER,
                    border_radius=60,
                )
            except:
                pass
        
        return ft.Container(
            content=ft.Icon(ft.Icons.PERSON, size=50, color=ft.Colors.GREY_400),
            width=120,
            height=120,
            border_radius=60,
            bgcolor=ft.Colors.GREY_200,
            alignment=ft.alignment.center,
        )

    def close_dialog(self):
        # Close current dialog
        if self.current_dialog:
            self.page.overlay.remove(self.current_dialog)
            self.current_dialog = None
            self.page.update()

    def show_add_dialog(self, e):
        # Show add contact dialog
        self.close_dialog()
        
        selected_photo_path = None
        photo_preview = self.create_photo_preview(None)
        
        # Form fields
        first_name = ft.TextField(label="نام *", width=350, border_color=ft.Colors.ORANGE_400)
        last_name = ft.TextField(label="نام خانوادگی *", width=350, border_color=ft.Colors.ORANGE_400)
        position = ft.TextField(label="سمت اجرایی", width=350, border_color=ft.Colors.ORANGE_400)
        email = ft.TextField(label="ایمیل", width=350, border_color=ft.Colors.ORANGE_400)
        
        # Phone field with validation
        phone = ft.TextField(
            label="تلفن *", 
            width=350, 
            border_color=ft.Colors.ORANGE_400,
            prefix_text="+98 ",
            hint_text="09123456789",
            helper_text="فرمت‌های قابل قبول: 09123456789 یا 02187654321",
            on_change=lambda e: self.validate_phone_field_in_dialog(e.control, phone_error_text)
        )
        
        phone_error_text = ft.Text("", size=12, color=ft.Colors.RED, visible=False)
        
        def validate_phone_field_in_dialog(phone_field, error_text):
            # Validate phone in real-time
            phone_value = phone_field.value.strip()
            if phone_value:
                is_valid, _ = self.validate_phone(phone_value)
                if is_valid:
                    phone_field.border_color = ft.Colors.GREEN
                    error_text.visible = False
                else:
                    phone_field.border_color = ft.Colors.RED
                    error_text.value = "شماره تلفن نامعتبر است"
                    error_text.visible = True
            else:
                phone_field.border_color = ft.Colors.ORANGE_400
                error_text.visible = False
            self.page.update()
        
        group_dropdown = ft.Dropdown(
            label="گروه آموزشی *",
            width=400,
            border_color=ft.Colors.ORANGE_400,
            options=[
                ft.dropdown.Option("برق"),
                ft.dropdown.Option("مکانیک"),
                ft.dropdown.Option("کامپیوتر"),
                ft.dropdown.Option("IT"),
                ft.dropdown.Option("نرم‌افزار"),
                ft.dropdown.Option("معماری"),
                ft.dropdown.Option("شیمی"),
            ],
            hint_text="انتخاب کنید"
        )
        
        file_picker = ft.FilePicker()
        
        def handle_photo_selection(e: ft.FilePickerResultEvent):
            # Handle photo file selection
            nonlocal selected_photo_path
            
            if e.files and len(e.files) > 0:
                selected_file = e.files[0]
                file_ext = os.path.splitext(selected_file.name)[1].lower()
                
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
                if file_ext not in allowed_extensions:
                    return
                
                try:
                    selected_photo_path = selected_file.path
                    
                    with open(selected_photo_path, 'rb') as f:
                        image_bytes = f.read()
                        photo_base64 = base64.b64encode(image_bytes).decode()
                    
                    photo_preview.content = ft.Image(
                        src_base64=photo_base64,
                        width=100,
                        height=100,
                        fit=ft.ImageFit.COVER,
                        border_radius=60,
                    )
                    
                    photo_preview.update()
                    
                except Exception:
                    pass
        
        file_picker.on_result = handle_photo_selection
        self.page.overlay.append(file_picker)
        
        def save_contact(e):
            # Validate required fields
            required_fields = [
                ("نام", first_name.value),
                ("نام خانوادگی", last_name.value),
                ("گروه آموزشی", group_dropdown.value),
                ("تلفن", phone.value)
            ]
            
            missing_fields = []
            for field_name, field_value in required_fields:
                if not field_value or not field_value.strip():
                    missing_fields.append(field_name)
            
            if missing_fields:
                self.show_validation_error(f"فیلدهای اجباری خالی هستند: {', '.join(missing_fields)}")
                return
            
            # Validate phone
            is_valid, formatted_phone = self.validate_phone(phone.value)
            if not is_valid:
                self.show_validation_error("شماره تلفن نامعتبر است")
                return
            
            contact_data = {
                'first_name': first_name.value.strip(),
                'last_name': last_name.value.strip(),
                'position': position.value.strip() if position.value else '',
                'email': email.value.strip() if email.value else '',
                'phone': formatted_phone,
                'group_name': group_dropdown.value,
                'photo_path': ''
            }
            
            # Save photo if selected
            if selected_photo_path:
                try:
                    file_ext = os.path.splitext(selected_photo_path)[1]
                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    save_path = os.path.join(self.photos_dir, unique_filename)
                    
                    shutil.copy2(selected_photo_path, save_path)
                    contact_data['photo_path'] = save_path
                except Exception:
                    pass
            
            success, message = self.db.add_contact(contact_data)
            if success:
                self.close_dialog()
                self.load_contacts()
                self.show_success_message("مخاطب با موفقیت اضافه شد")
            else:
                self.show_validation_error(message)
        
        def close_dialog_local(e):
            # Close dialog
            self.close_dialog()
        
        form_column = ft.Column(
            spacing=15,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.PERSON_ADD, color=ft.Colors.ORANGE_600),
                    ft.Text("افزودن مخاطب جدید", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_800),
                ], alignment=ft.MainAxisAlignment.CENTER),
                
                ft.Divider(color=ft.Colors.GREY_300),
                
                ft.Row([
                    ft.Column([
                        ft.Text("عکس پروفایل", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800),
                        photo_preview,
                        ft.ElevatedButton(
                            "انتخاب عکس",
                            icon=ft.Icons.IMAGE,
                            on_click=lambda e: file_picker.pick_files(
                                allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp"],
                                allow_multiple=False
                            ),
                            width=120,
                            height=40,
                        )
                    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    
                    ft.VerticalDivider(width=20),
                    
                    ft.Column([
                        ft.Row([
                            ft.Column([
                                ft.Text("نام *", size=12, color=ft.Colors.GREY_700),
                                first_name
                            ], spacing=5),
                            ft.Container(width=20),
                            ft.Column([
                                ft.Text("نام خانوادگی *", size=12, color=ft.Colors.GREY_700),
                                last_name
                            ], spacing=5)
                        ]),
                        
                        ft.Row([
                            ft.Column([
                                ft.Text("سمت اجرایی", size=12, color=ft.Colors.GREY_700),
                                position
                            ], spacing=5),
                            ft.Container(width=20),
                            ft.Column([
                                ft.Text("ایمیل", size=12, color=ft.Colors.GREY_700),
                                email
                            ], spacing=5)
                        ]),
                    ], spacing=15)
                ]),
                
                ft.Divider(color=ft.Colors.GREY_300),
                
                ft.Column([
                    ft.Text("گروه آموزشی *", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800),
                    group_dropdown
                ], spacing=10),
                
                ft.Divider(color=ft.Colors.GREY_300),
                
                ft.Column([
                    ft.Text("شماره تلفن *", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800),
                    phone,
                    phone_error_text
                ], spacing=10),
                
                ft.Container(height=20),
                
                ft.Row([
                    ft.ElevatedButton(
                        "انصراف",
                        icon=ft.Icons.CANCEL,
                        on_click=close_dialog_local,
                        bgcolor=ft.Colors.GREY_200,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.ElevatedButton(
                        "افزودن مخاطب",
                        icon=ft.Icons.CHECK_CIRCLE,
                        on_click=save_contact,
                        bgcolor=ft.Colors.ORANGE_400,
                        color=ft.Colors.WHITE,
                    )
                ], alignment=ft.MainAxisAlignment.END, spacing=10)
            ],
            scroll="auto",
        )
        
        form_container = ft.Container(
            content=form_column,
            width=1100,
            height=650,
            padding=30,
            bgcolor=ft.Colors.WHITE,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK54),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        
        overlay_container = ft.Container(
            content=form_container,
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.BLACK54,
        )
        
        self.current_dialog = overlay_container
        self.page.overlay.append(overlay_container)
        self.page.update()

    def show_add_csv_dialog(self, e):
        # Show CSV import dialog
        self.close_dialog()
        
        contacts_from_file = []
        
        def handle_file_pick(e: ft.FilePickerResultEvent):
            # Process CSV file
            contacts_from_file.clear()
            
            if e.files and e.files[0].path:
                try:
                    file_path = e.files[0].path
                    with open(file_path, 'r', encoding='utf-8-sig') as file:
                        file_content = file.read()
                    
                    csv_file = StringIO(file_content)
                    reader = csv.DictReader(csv_file)
                    
                    required_columns = ["first_name", "last_name", "group_name", "phone"]
                    
                    if reader.fieldnames:
                        missing_headers = [col for col in required_columns if col not in reader.fieldnames]
                        if missing_headers:
                            self.show_validation_error(f"ستون‌های ضروری وجود ندارند: {', '.join(missing_headers)}")
                            return
                    
                    row_num = 0
                    valid_rows = 0
                    invalid_rows = []
                    
                    for row in reader:
                        row_num += 1
                        
                        # Validate required fields
                        missing_columns = [col for col in required_columns if not row.get(col)]
                        if missing_columns:
                            invalid_rows.append(f"ردیف {row_num}: فیلدهای خالی {', '.join(missing_columns)}")
                            continue
                        
                        # Validate phone
                        phone_value = row.get('phone', '').strip()
                        is_valid, formatted_phone = self.validate_phone(phone_value)
                        if not is_valid:
                            invalid_rows.append(f"ردیف {row_num}: شماره تلفن نامعتبر - {phone_value}")
                            continue
                        
                        contacts_from_file.append({
                            'first_name': row.get('first_name', '').strip(),
                            'last_name': row.get('last_name', '').strip(),
                            'group_name': row.get('group_name', '').strip(),
                            'position': row.get('position', '').strip(),
                            'email': row.get('email', '').strip(),
                            'phone': formatted_phone
                        })
                        valid_rows += 1
                    
                    if invalid_rows and len(invalid_rows) > 0:
                        error_msg = f"{len(invalid_rows)} ردیف نامعتبر یافت شد"
                        if len(invalid_rows) <= 3:
                            error_msg += ":\n" + "\n".join(invalid_rows)
                        else:
                            error_msg += f" (نمایش 3 مورد اول):\n" + "\n".join(invalid_rows[:3])
                        self.show_validation_error(error_msg)
                    
                    if contacts_from_file:
                        save_button.disabled = False
                        self.show_success_message(f"{valid_rows} ردیف معتبر یافت شد")
                    else:
                        save_button.disabled = True
                        self.show_validation_error("هیچ ردیف معتبری یافت نشد")
                        
                except Exception as e:
                    self.show_validation_error(f"خطا در خواندن فایل: {str(e)}")
            
            self.page.update()
        
        def save_contacts_from_file(e):
            # Save all valid contacts from CSV
            if not contacts_from_file:
                return
            
            success_count = 0
            error_count = 0
            duplicate_count = 0
            
            for contact in contacts_from_file:
                success, message = self.db.add_contact(contact)
                if success:
                    success_count += 1
                elif "قبلاً ثبت شده" in message:
                    duplicate_count += 1
                else:
                    error_count += 1
            
            self.close_dialog()
            self.load_contacts()
            
            result_msg = f"نتیجه:\n"
            result_msg += f"✅ {success_count} مخاطب اضافه شد\n"
            if duplicate_count > 0:
                result_msg += f"⚠️ {duplicate_count} تکراری\n"
            if error_count > 0:
                result_msg += f"❌ {error_count} خطا"
            
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(result_msg, color=ft.Colors.WHITE),
                bgcolor=ft.Colors.GREEN_400 if success_count > 0 else ft.Colors.ORANGE_400,
                duration=5000,
            )
            self.page.snack_bar.open = True
            self.page.update()
        
        def close_dialog_local(e):
            # Close dialog
            self.close_dialog()
        
        file_picker = ft.FilePicker()
        file_picker.on_result = handle_file_pick
        self.page.overlay.append(file_picker)
        
        save_button = ft.ElevatedButton(
            "ذخیره مخاطبین",
            icon=ft.Icons.SAVE,
            on_click=save_contacts_from_file,
            bgcolor=ft.Colors.ORANGE_400,
            color=ft.Colors.WHITE,
            disabled=True,
        )
        
        form_column = ft.Column(
            spacing=15,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.UPLOAD_FILE, color=ft.Colors.ORANGE_600),
                    ft.Text("افزودن مخاطب از فایل CSV", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_800),
                ], alignment=ft.MainAxisAlignment.CENTER),
                
                ft.Divider(color=ft.Colors.GREY_300),
                
                ft.Column([
                    ft.Text("انتخاب فایل CSV", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800),
                    ft.Text("فقط فایل‌های با فرمت CSV پشتیبانی می‌شوند", size=11, color=ft.Colors.GREY_600),
                    
                    ft.Row([
                        ft.ElevatedButton(
                            "انتخاب فایل CSV",
                            icon=ft.Icons.FILE_UPLOAD,
                            on_click=lambda e: file_picker.pick_files(
                                allowed_extensions=["csv"],
                                allow_multiple=False
                            ),
                            bgcolor=ft.Colors.ORANGE_400,
                            color=ft.Colors.WHITE,
                        ),
                    ], spacing=20, alignment=ft.MainAxisAlignment.START),
                ], spacing=10),
                
                ft.Divider(color=ft.Colors.GREY_300),
                
                ft.Container(
                    content=ft.Column([
                        ft.Text("راهنمای فرمت فایل CSV:", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                        ft.Text("• ستون‌های اجباری: first_name, last_name, group_name, phone", size=10, color=ft.Colors.GREY_600),
                        ft.Text("• ستون‌های اختیاری: position, email", size=10, color=ft.Colors.GREY_600),
                        ft.Text("• فایل باید با UTF-8 ذخیره شده باشد", size=10, color=ft.Colors.GREY_600),
                        ft.Text("• فرمت تلفن: 09123456789 یا 02187654321", size=10, color=ft.Colors.GREY_600),
                        ft.Text("• نمونه فایل: first_name,last_name,group_name,position,email,phone", size=10, color=ft.Colors.GREY_600),
                    ], spacing=5),
                    padding=10,
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=8,
                ),
                
                ft.Container(height=10),
                
                ft.Row([
                    ft.ElevatedButton(
                        "انصراف",
                        icon=ft.Icons.CANCEL,
                        on_click=close_dialog_local,
                        bgcolor=ft.Colors.GREY_200,
                        color=ft.Colors.GREY_700,
                    ),
                    save_button
                ], alignment=ft.MainAxisAlignment.END, spacing=10)
            ],
            scroll="auto",
        )
        
        form_container = ft.Container(
            content=form_column,
            width=800,
            height=550,
            padding=30,
            bgcolor=ft.Colors.WHITE,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK54),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        
        overlay_container = ft.Container(
            content=form_container,
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.BLACK54,
        )
        
        self.current_dialog = overlay_container
        self.page.overlay.append(overlay_container)
        self.page.update()

    def edit_contact(self, contact_id):
        # Show edit contact dialog
        self.close_dialog()
        
        contacts = self.db.get_all()
        contact_to_edit = None
        for contact in contacts:
            if contact.get("id") == contact_id:
                contact_to_edit = contact
                break
        
        if not contact_to_edit:
            return
        
        selected_photo_path = None
        current_photo_path = contact_to_edit.get("photo_path")
        photo_preview = self.create_photo_preview(current_photo_path)
        
        first_name_field = ft.TextField(
            label="نام *", 
            value=contact_to_edit.get("first_name", ""), 
            width=350, 
            border_color=ft.Colors.ORANGE_400
        )
        
        last_name_field = ft.TextField(
            label="نام خانوادگی *", 
            value=contact_to_edit.get("last_name", ""), 
            width=350, 
            border_color=ft.Colors.ORANGE_400
        )
        
        group_options = [
            "برق", "مکانیک", "کامپیوتر", "IT", 
            "نرم‌افزار", "معماری", "شیمی"
        ]
        
        group_dropdown = ft.Dropdown(
            label="گروه آموزشی *",
            width=350,
            border_color=ft.Colors.ORANGE_400,
            options=[ft.dropdown.Option(g) for g in group_options],
            value=contact_to_edit.get("group_name", ""),
        )
        
        position_field = ft.TextField(
            label="سمت اجرایی", 
            value=contact_to_edit.get("position", ""), 
            width=350, 
            border_color=ft.Colors.ORANGE_400
        )
        
        email_field = ft.TextField(
            label="ایمیل", 
            value=contact_to_edit.get("email", ""), 
            width=350, 
            border_color=ft.Colors.ORANGE_400
        )
        
        phone_field = ft.TextField(
            label="تلفن *", 
            value=contact_to_edit.get("phone", ""), 
            width=350, 
            border_color=ft.Colors.ORANGE_400,
            prefix_text="+98 ",
            on_change=lambda e: self.validate_phone_field_in_dialog(e.control, phone_error_text)
        )
        
        phone_error_text = ft.Text("", size=12, color=ft.Colors.RED, visible=False)
        
        def validate_phone_field_in_dialog(phone_field, error_text):
            # Validate phone in real-time
            phone_value = phone_field.value.strip()
            if phone_value:
                is_valid, _ = self.validate_phone(phone_value)
                if is_valid:
                    phone_field.border_color = ft.Colors.GREEN
                    error_text.visible = False
                else:
                    phone_field.border_color = ft.Colors.RED
                    error_text.value = "شماره تلفن نامعتبر است"
                    error_text.visible = True
            else:
                phone_field.border_color = ft.Colors.ORANGE_400
                error_text.visible = False
            self.page.update()
        
        file_picker = ft.FilePicker()
        
        def handle_photo_selection(e: ft.FilePickerResultEvent):
            # Handle photo file selection
            nonlocal selected_photo_path
            
            if e.files and len(e.files) > 0:
                selected_file = e.files[0]
                file_ext = os.path.splitext(selected_file.name)[1].lower()
                
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
                if file_ext not in allowed_extensions:
                    return
                
                try:
                    selected_photo_path = selected_file.path
                    
                    with open(selected_photo_path, 'rb') as f:
                        image_bytes = f.read()
                        photo_base64 = base64.b64encode(image_bytes).decode()
                    
                    photo_preview.content = ft.Image(
                        src_base64=photo_base64,
                        width=120,
                        height=120,
                        fit=ft.ImageFit.COVER,
                        border_radius=60,
                    )
                    
                    photo_preview.update()
                    
                except Exception:
                    pass
        
        file_picker.on_result = handle_photo_selection
        self.page.overlay.append(file_picker)
        
        def save_changes(e):
            # Validate required fields
            required_fields = [
                ("نام", first_name_field.value),
                ("نام خانوادگی", last_name_field.value),
                ("گروه آموزشی", group_dropdown.value),
                ("تلفن", phone_field.value)
            ]
            
            missing_fields = []
            for field_name, field_value in required_fields:
                if not field_value or not field_value.strip():
                    missing_fields.append(field_name)
            
            if missing_fields:
                self.show_validation_error(f"فیلدهای اجباری خالی هستند: {', '.join(missing_fields)}")
                return
            
            # Validate phone
            is_valid, formatted_phone = self.validate_phone(phone_field.value)
            if not is_valid:
                self.show_validation_error("شماره تلفن نامعتبر است")
                return
            
            updated_data = {
                'first_name': first_name_field.value.strip(),
                'last_name': last_name_field.value.strip(),
                'group_name': group_dropdown.value,
                'position': position_field.value.strip() if position_field.value else '',
                'email': email_field.value.strip() if email_field.value else '',
                'phone': formatted_phone
            }
            
            # Update photo if changed
            if selected_photo_path:
                try:
                    file_ext = os.path.splitext(selected_photo_path)[1]
                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    save_path = os.path.join(self.photos_dir, unique_filename)
                    
                    if current_photo_path and os.path.exists(current_photo_path):
                        try:
                            os.remove(current_photo_path)
                        except:
                            pass
                    
                    shutil.copy2(selected_photo_path, save_path)
                    updated_data['photo_path'] = save_path
                    
                except Exception:
                    pass
            
            success, _ = self.db.update(contact_id, updated_data)
            
            if success:
                self.close_dialog()
                self.load_contacts()
                self.show_success_message("مخاطب با موفقیت به‌روزرسانی شد")
            else:
                self.show_validation_error("خطا در به‌روزرسانی")
        
        def close_dialog_local(e):
            # Close dialog
            self.close_dialog()
        
        form_column = ft.Column(
            spacing=15,
            controls=[
                ft.Row([
                    ft.Icon(ft.Icons.EDIT, color=ft.Colors.ORANGE_600),
                    ft.Text("ویرایش مخاطب", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_800),
                ], alignment=ft.MainAxisAlignment.CENTER),
                
                ft.Divider(color=ft.Colors.GREY_300),
                
                ft.Row([
                    ft.Column([
                        ft.Text("عکس پروفایل", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800),
                        photo_preview,
                        ft.ElevatedButton(
                            "تغییر عکس",
                            icon=ft.Icons.IMAGE,
                            on_click=lambda e: file_picker.pick_files(
                                allowed_extensions=["jpg", "jpeg", "png", "gif", "bmp"],
                                allow_multiple=False
                            ),
                            width=120,
                            height=40,
                        )
                    ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    
                    ft.VerticalDivider(width=20),
                    
                    ft.Column([
                        ft.Row([
                            ft.Column([
                                ft.Text("نام *", size=12, color=ft.Colors.GREY_700),
                                first_name_field
                            ], spacing=5),
                            ft.Container(width=20),
                            ft.Column([
                                ft.Text("نام خانوادگی *", size=12, color=ft.Colors.GREY_700),
                                last_name_field
                            ], spacing=5)
                        ]),
                        
                        ft.Row([
                            ft.Column([
                                ft.Text("سمت اجرایی", size=12, color=ft.Colors.GREY_700),
                                position_field
                            ], spacing=5),
                            ft.Container(width=20),
                            ft.Column([
                                ft.Text("ایمیل", size=12, color=ft.Colors.GREY_700),
                                email_field
                            ], spacing=5)
                        ]),
                    ], spacing=15)
                ]),
                
                ft.Divider(color=ft.Colors.GREY_300),
                
                ft.Column([
                    ft.Text("گروه آموزشی *", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800),
                    group_dropdown
                ], spacing=10),
                
                ft.Divider(color=ft.Colors.GREY_300),
                
                ft.Column([
                    ft.Text("شماره تلفن *", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_800),
                    phone_field,
                    phone_error_text
                ], spacing=10),
                
                ft.Container(height=20),
                
                ft.Row([
                    ft.ElevatedButton(
                        "انصراف",
                        icon=ft.Icons.CANCEL,
                        on_click=close_dialog_local,
                        bgcolor=ft.Colors.GREY_200,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.ElevatedButton(
                        "ذخیره تغییرات",
                        icon=ft.Icons.CHECK_CIRCLE,
                        on_click=save_changes,
                        bgcolor=ft.Colors.ORANGE_400,
                        color=ft.Colors.WHITE,
                    )
                ], alignment=ft.MainAxisAlignment.END, spacing=10)
            ],
            scroll="auto",
        )
        
        form_container = ft.Container(
            content=form_column,
            width=1100,
            height=650,
            padding=30,
            bgcolor=ft.Colors.WHITE,
            border_radius=15,
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK54),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        
        overlay_container = ft.Container(
            content=form_container,
            alignment=ft.alignment.center,
            expand=True,
            bgcolor=ft.Colors.BLACK54,
        )
        
        self.current_dialog = overlay_container
        self.page.overlay.append(overlay_container)
        self.page.update()

    def delete_contact(self, contact_id):
        # Delete contact and associated photo
        success, _ = self.db.delete(contact_id)
        
        if success:
            contacts = self.db.get_all()
            for contact in contacts:
                if contact.get("id") == contact_id and contact.get("photo_path"):
                    try:
                        photo_path = contact.get("photo_path")
                        if os.path.exists(photo_path):
                            os.remove(photo_path)
                    except:
                        pass
        
        self.load_contacts()
        self.show_success_message("مخاطب با موفقیت حذف شد")

    def build_ui(self):
        # Build main UI layout
        self.page.add(
            ft.Column(
                spacing=20,
                controls=[
                    self.build_header(),
                    self.hero_title(),
                    self.build_search_box(),
                    self.build_admin_actions(),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.LIST, color=ft.Colors.ORANGE_400),
                                ft.Text("جدول مخاطبین", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.ORANGE_800),
                            ]),
                            ft.Container(
                                content=self.contacts_container,
                                padding=15,
                                border_radius=12,
                                border=ft.border.all(1, ft.Colors.GREY_300),
                                bgcolor=ft.Colors.WHITE,
                                shadow=ft.BoxShadow(blur_radius=3, color=ft.Colors.BLACK12),
                            )
                        ], spacing=10),
                    )
                ],
            )
        )


def main(page: ft.Page):
    # Main entry point
    page.assets_dir = "assets"
    app = PhoneBookApp(page)


if __name__ == "__main__":
    ft.app(target=main)