"""
Punto de Venta (POS) — Tortas Susy
Flet 0.84+ | SQLite3 | JSON | OOP
"""
import flet as ft
import sqlite3, json, os, copy
import asyncio
import ssl
from datetime import datetime

ssl._create_default_https_context = ssl._create_unverified_context

try:
    import win32print
    WIN32_PRINT_AVAILABLE = True
except ImportError:
    WIN32_PRINT_AVAILABLE = False

try:
    import win32ui, win32con
    WIN32_GDI_AVAILABLE = True
except ImportError:
    WIN32_GDI_AVAILABLE = False

WIN32_AVAILABLE = WIN32_PRINT_AVAILABLE

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False

DB_PATH = "clientes.db"
PEDIDOS_PATH = "pedidos_dia.json"
PEDIDOS_TXT_TEMPLATE = "pedidos_{fecha}.txt"

MENU = {
    "Comida": [("Torta",60),("Torta Mini",30),("Taco Dorado",10),("Taco c/Carne",25),("Kilo de Carne",300),("Crear Producto",0)],
    "Paquetes": [("Paquete #1",90),("Paquete #2",95),("Paquete #3",220),("Paquete #4",345),("Paquete #5",680)],
    "Bebidas": [("Refresco",30),("Cerveza",25),("Agua Fresca 500ml",15),("Agua Fresca 1LT",25),("Caguama",70)],
}

MEAT_TYPES = ["Carne","Buche","Lengua","Mixta"]
TACO_TYPES = ["Papa","Frijol","Requesón","Picadillo"]
REFRESCO_TYPES = ["Coca","Fanta","Manzana","Sprite"]
DRINK_TYPES = ["Coca","Fanta","Manzana","Sprite","Jamaica","Horchata"]
BEER_TYPES = ["Clara","Obscura"]
AGUA_TYPES = ["Jamaica","Horchata"]
GRID_COLORS = {"Comida":"#F5E7D0","Paquetes":"#EEDCC1","Bebidas":"#F9EFE0"}

BG_DARK="#F2E6D3"; BG_CARD="#FFFDF8"; ACCENT="#B33939"
ACCENT2="#D8C1A0"; TXT="#4A2A22"; GREEN="#16A34A"; GOLD="#8F2D2D"
ERROR_RED="#8B1E1E"
BG_PANEL="#FBF4E8"; BG_ITEM="#F3E6D3"; TXT_MUTED="#8A6F5A"; INPUT_BG="#FFFFFF"
# Tonos extendidos para una estética moderna (mantienen la paleta cálida)
SURFACE_HIGH="#FFFEFB"
SURFACE_LOW="#EFE0C8"
ACCENT_SOFT="#E8D4B8"
ACCENT_DARK="#7A1F1F"
HIGHLIGHT="#F7B267"
DIVIDER_SOFT="#E5D3B7"
SHADOW_BLACK_LIGHT=ft.Colors.with_opacity(0.10,"black")
SHADOW_BLACK_MED=ft.Colors.with_opacity(0.18,"black")
SHADOW_BLACK_STRONG=ft.Colors.with_opacity(0.30,"black")

# Iconografía visual por producto (emoji decorativo grande)
PRODUCT_ICONS={
    "Torta":"\U0001F96A",
    "Torta Mini":"\U0001F35E",
    "Taco Dorado":"\U0001F32E",
    "Taco c/Carne":"\U0001F32F",
    "Kilo de Carne":"\U0001F969",
    "Crear Producto":"✨",
    "Paquete #1":"\U0001F381",
    "Paquete #2":"\U0001F381",
    "Paquete #3":"\U0001F4E6",
    "Paquete #4":"\U0001F4E6",
    "Paquete #5":"\U0001F38A",
    "Refresco":"\U0001F964",
    "Cerveza":"\U0001F37A",
    "Agua Fresca 500ml":"\U0001F378",
    "Agua Fresca 1LT":"\U0001F378",
    "Caguama":"\U0001F37B",
}
CATEGORY_ICONS={"Comida":"\U0001F354","Paquetes":"\U0001F4E6","Bebidas":"\U0001F964"}

TICKET_TEXT_WIDTH = 32
PRODUCTO_ANCHO = 14
CANTIDAD_ANCHO = 6
PRECIO_ANCHO = 10
TICKET_FONT_NAME = "Arial"
TICKET_FONT_HEIGHT = 30
TICKET_FONT_WEIGHT = win32con.FW_NORMAL if WIN32_GDI_AVAILABLE else 400
TICKET_MARGIN_X = 20
TICKET_MARGIN_Y = 20
TICKET_LINE_STEP = 30

def play_notification_sound(kind: str):
    if not WINSOUND_AVAILABLE:
        return
    if kind=="print_success":
        winsound.MessageBeep(winsound.MB_OK)
    elif kind=="print_error":
        winsound.MessageBeep(winsound.MB_ICONHAND)
    elif kind=="clean_success":
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    elif kind=="list_click":
        winsound.Beep(1200, 45)
    else:
        winsound.Beep(900, 45)

# ─── DB ───
def init_db():
    c=sqlite3.connect(DB_PATH); c.execute(
        "CREATE TABLE IF NOT EXISTS clientes(telefono TEXT PRIMARY KEY,domicilio TEXT,cruces TEXT)"
    ); c.commit(); c.close()

def _columnas_clientes(cnx):
    return {r[1] for r in cnx.execute("PRAGMA table_info(clientes)").fetchall()}

def buscar_cliente(tel):
    c=sqlite3.connect(DB_PATH); r=c.execute(
        "SELECT domicilio,cruces FROM clientes WHERE telefono=?",(tel,)
    ).fetchone(); c.close(); return r

def guardar_cliente(tel,dom,cru):
    c=sqlite3.connect(DB_PATH)
    cols=_columnas_clientes(c)
    if "usuario" in cols:
        c.execute(
            "INSERT OR REPLACE INTO clientes(telefono,usuario,domicilio,cruces) VALUES(?,?,?,?)",
            (tel,"",dom,cru),
        )
    else:
        c.execute(
            "INSERT OR REPLACE INTO clientes(telefono,domicilio,cruces) VALUES(?,?,?)",
            (tel,dom,cru),
        )
    c.commit(); c.close()

# ─── JSON ───
def _leer_pedidos_json():
    if not os.path.exists(PEDIDOS_PATH):
        return []
    with open(PEDIDOS_PATH,"r",encoding="utf-8") as f:
        try:
            data=json.load(f)
        except json.JSONDecodeError:
            return []
    return data if isinstance(data,list) else []

def _guardar_pedidos_json(pedidos):
    with open(PEDIDOS_PATH,"w",encoding="utf-8") as f:
        json.dump(pedidos,f,ensure_ascii=False,indent=2)

def _ruta_pedidos_txt(fecha: str):
    return PEDIDOS_TXT_TEMPLATE.format(fecha=fecha)

def _archivar_pedidos_txt(fecha: str, pedidos: list[dict]):
    if not pedidos:
        return
    ruta=_ruta_pedidos_txt(fecha)
    with open(ruta,"a",encoding="utf-8") as f:
        for p in pedidos:
            f.write(generar_ticket_impresion(p))
            f.write("\n"+"-"*TICKET_TEXT_WIDTH+"\n")

def cargar_pedidos():
    pedidos=_leer_pedidos_json()
    if not pedidos:
        return []
    hoy=datetime.now().strftime("%Y-%m-%d")
    pedidos_hoy=[]
    pedidos_historicos: dict[str, list[dict]]={}
    for p in pedidos:
        fecha=str(p.get("fecha","")).strip()
        if fecha and fecha!=hoy:
            pedidos_historicos.setdefault(fecha,[]).append(p)
        else:
            pedidos_hoy.append(p)
    for fecha,pedidos_fecha in pedidos_historicos.items():
        _archivar_pedidos_txt(fecha,pedidos_fecha)
    if pedidos_historicos:
        _guardar_pedidos_json(pedidos_hoy)
    return pedidos_hoy

def guardar_pedido(p):
    ps=cargar_pedidos()
    ps.append(p)
    _guardar_pedidos_json(ps)

def eliminar_pedido(pedido):
    pedidos_hoy=cargar_pedidos()
    for i,p in enumerate(pedidos_hoy):
        if p==pedido:
            pedidos_hoy.pop(i)
            _guardar_pedidos_json(pedidos_hoy)
            return True
    return False

# ─── Ticket 32 chars ───
def centrar(texto, ancho=TICKET_TEXT_WIDTH):
    return str(texto or "")[:ancho].center(ancho)

def dividir_texto(texto, ancho_max=TICKET_TEXT_WIDTH):
    ws=str(texto or "").split(); ls=[]; cur=""
    for w in ws:
        if len(w)>ancho_max:
            if cur: ls.append(cur); cur=""
            while len(w)>ancho_max: ls.append(w[:ancho_max]); w=w[ancho_max:]
            if w: cur=w
        elif not cur: cur=w
        elif len(cur)+1+len(w)<=ancho_max: cur+=" "+w
        else: ls.append(cur); cur=w
    if cur: ls.append(cur)
    return ls or [""]

def dividir_campo(campo, valor, ancho_max=TICKET_TEXT_WIDTH):
    return dividir_texto(f"{campo}: {valor}", ancho_max=ancho_max)

def formatear_moneda(valor):
    try:
        n=float(valor)
    except (TypeError, ValueError):
        return f"${valor}"
    if n.is_integer(): return f"${int(n)}"
    return f"${n:.2f}"

def formatear_renglon_producto(item):
    nombre=str(item.get("name",""))[:PRODUCTO_ANCHO].ljust(PRODUCTO_ANCHO)
    qty=item.get("qty",0)
    if isinstance(qty,float) and qty.is_integer(): qty=int(qty)
    cantidad=str(qty).center(CANTIDAD_ANCHO)
    try:
        subtotal=float(item.get("price",0))*float(item.get("qty",0))
    except (TypeError, ValueError):
        subtotal=0
    precio=formatear_moneda(subtotal).rjust(PRECIO_ANCHO)
    return f"{nombre}{cantidad}{precio}"

def generar_ticket_impresion(ped):
    s="="*TICKET_TEXT_WIDTH
    t=[centrar("TORTAS SUSY"),s]
    t.extend(dividir_campo("Fecha",ped.get("fecha","")))
    t.extend(dividir_campo("Hora",ped.get("hora","")))
    t.append(s)
    for l,k in [("Tel","telefono"),("Dom","domicilio"),("Cruces","cruces"),("Hr esp","hora_especifica")]:
        v=ped.get(k,"")
        if v: t.extend(dividir_campo(l,v))
    t+=[s,centrar("PEDIDO"),"-"*TICKET_TEXT_WIDTH,
        f"{'Producto'.ljust(PRODUCTO_ANCHO)}{'Cant'.center(CANTIDAD_ANCHO)}{'Precio'.rjust(PRECIO_ANCHO)}",
        "-"*TICKET_TEXT_WIDTH]
    for pl in ped.get("platos",[]):
        t.extend(dividir_texto(f"[{pl['nombre']}]"))
        for it in pl.get("items",[]):
            t.append(formatear_renglon_producto(it))
            vr=it.get('variant','')
            if vr: t.extend(dividir_texto(f"-> {vr}"))
    total_txt=formatear_moneda(ped.get("total",0))
    t+=[s,f"{'TOTAL:'.ljust(TICKET_TEXT_WIDTH-PRECIO_ANCHO)}{total_txt.rjust(PRECIO_ANCHO)}",
        s,centrar("Gracias por su compra!"),"","",""]
    return "\n".join(t)


# ═══════════════════════════════════════
#  IMPRESORA FÍSICA (win32print)
# ═══════════════════════════════════════
class TicketPrinter:
    """Gestiona la impresión física en impresora térmica vía win32print."""
    def __init__(self):
        self.printer_name = None
        if WIN32_PRINT_AVAILABLE:
            try:
                self.printer_name = win32print.GetDefaultPrinter()
            except Exception:
                self.printer_name = None

    def _imprimir_raw(self, ticket_text: str):
        hprinter=win32print.OpenPrinter(self.printer_name)
        try:
            win32print.StartDocPrinter(hprinter, 1, ("Ticket POS", None, "RAW"))
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, ticket_text.encode("utf-8"))
            win32print.EndPagePrinter(hprinter)
            win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)

    def _imprimir_gdi(self, ticket_text: str):
        dc=win32ui.CreateDC()
        dc.CreatePrinterDC(self.printer_name)
        font=win32ui.CreateFont({"name":TICKET_FONT_NAME,"height":TICKET_FONT_HEIGHT,"weight":TICKET_FONT_WEIGHT})
        old_font=None
        try:
            dc.StartDoc("Ticket POS")
            dc.StartPage()
            old_font=dc.SelectObject(font)
            y=TICKET_MARGIN_Y
            limite=dc.GetDeviceCaps(win32con.VERTRES)-TICKET_MARGIN_Y
            for line in ticket_text.split("\n"):
                if y>limite:
                    dc.EndPage()
                    dc.StartPage()
                    dc.SelectObject(font)
                    y=TICKET_MARGIN_Y
                dc.TextOut(TICKET_MARGIN_X,y,line)
                y+=TICKET_LINE_STEP
            dc.EndPage()
            dc.EndDoc()
        finally:
            if old_font: dc.SelectObject(old_font)
            dc.DeleteDC()

    def imprimir(self, ticket_text: str) -> tuple[bool, str]:
        """Envía el ticket a la impresora. Retorna (éxito, mensaje)."""
        if not WIN32_PRINT_AVAILABLE:
            return False, "win32print no disponible (pywin32 no instalado)"
        if not self.printer_name:
            return False, "No se detectó impresora por defecto"
        try:
            if WIN32_GDI_AVAILABLE:
                self._imprimir_gdi(ticket_text)
            else:
                self._imprimir_raw(ticket_text)
            return True, "Ticket enviado a impresora"
        except Exception as ex:
            return False, f"Error al imprimir: {ex}"

# Instancia global de impresora
printer = TicketPrinter()

# ═══════════════════════════════════════
#  DATA MODELS
# ═══════════════════════════════════════
class Plato:
    _n=0
    def __init__(self,nombre=None,items=None):
        if nombre is None: Plato._n+=1; nombre=f"Plato {Plato._n}"
        self.nombre=nombre; self.items=items or []
    def agregar(self,name,price,qty=1,variant=""):
        for i in self.items:
            if i["name"]==name and i.get("variant","")==variant and i["price"]==price:
                i["qty"]+=qty; return
        self.items.append({"name":name,"price":price,"qty":qty,"variant":variant})
    def total(self): return sum(i["price"]*i["qty"] for i in self.items)
    def to_dict(self): return {"nombre":self.nombre,"items":[dict(i) for i in self.items]}
    def clonar(self):
        Plato._n+=1; return Plato(f"Plato {Plato._n}",copy.deepcopy(self.items))

class PedidoState:
    def __init__(self):
        self.platos:list[Plato]=[]; self.activo=-1; self.cli_existe=False; Plato._n=0
    def crear_plato(self):
        p=Plato(); self.platos.append(p); self.activo=len(self.platos)-1; return p
    def eliminar(self,i):
        if 0<=i<len(self.platos):
            self.platos.pop(i)
            if self.activo>=len(self.platos): self.activo=len(self.platos)-1
    def duplicar(self,i):
        if 0<=i<len(self.platos): self.platos.insert(i+1,self.platos[i].clonar())
    def agregar_a_activo(self,name,price,qty=1,variant=""):
        if 0<=self.activo<len(self.platos): self.platos[self.activo].agregar(name,price,qty,variant); return True
        return False
    def mover_item(self,sp,si,dp):
        if sp==dp: return
        src=self.platos[sp]; item=src.items.pop(si)
        dst=self.platos[dp]
        for i in dst.items:
            if i["name"]==item["name"]: i["qty"]+=item["qty"]; return
        dst.items.append(item)
    def total(self): return sum(p.total() for p in self.platos)
    def limpiar(self): self.platos.clear(); self.activo=-1; Plato._n=0; self.cli_existe=False
    def cargar_desde_pedido(self,pedido):
        self.limpiar()
        for pd in pedido.get("platos",[]):
            nombre=str(pd.get("nombre","")).strip() or f"Plato {len(self.platos)+1}"
            items=[]
            for it in pd.get("items",[]):
                items.append({
                    "name":it.get("name",""),
                    "price":it.get("price",0),
                    "qty":it.get("qty",1),
                    "variant":it.get("variant",""),
                })
            self.platos.append(Plato(nombre,items))
        if self.platos:
            self.activo=0
            Plato._n=len(self.platos)

# ═══════════════════════════════════════
#  UI COMPONENTS
# ═══════════════════════════════════════
class FormularioCliente:
    def __init__(self,page,state):
        self.page=page; self.state=state
        ts=dict(dense=True,border_color=ACCENT2,color=TXT,bgcolor=INPUT_BG,text_size=13,height=40)
        self.tf_dom=ft.TextField(width=200,**ts)
        self.tf_cru=ft.TextField(width=200,**ts)
        self.tf_tel=ft.TextField(width=150,on_blur=self._buscar,on_submit=self._buscar,**ts)
        # Segmented buttons
        self.seg_tel=ft.SegmentedButton(
            segments=[ft.Segment(value="si",label=ft.Text("Sí",color=TXT)),ft.Segment(value="no",label=ft.Text("No",color=TXT))],
            selected=["si"],on_change=self._toggle_tel,allow_empty_selection=False)
        self.seg_hora=ft.SegmentedButton(
            segments=[ft.Segment(value="si",label=ft.Text("Sí",color=TXT)),ft.Segment(value="no",label=ft.Text("No",color=TXT))],
            selected=["no"],on_change=self._toggle_hora,allow_empty_selection=False)
        # Hour dropdowns
        dds=dict(
            dense=True,
            text_size=18,
            text_style=ft.TextStyle(size=18,weight=ft.FontWeight.W_700,color=TXT),
            border_color=ACCENT,
            focused_border_color=ACCENT,
            border_width=1.5,
            focused_border_width=2,
            color=TXT,
            bgcolor=INPUT_BG,
            filled=True,
            fill_color=INPUT_BG,
            content_padding=ft.Padding(12,10,12,10),
            height=52,
        )
        self.dd_h=ft.Dropdown(width=88,options=[ft.DropdownOption(key=str(i),text=str(i)) for i in range(1,13)],
                              value="12",disabled=True,**dds)
        self.dd_m=ft.Dropdown(width=88,options=[ft.DropdownOption(key=f"{i:02d}",text=f"{i:02d}") for i in range(0,60,10)],
                              value="00",disabled=True,**dds)
        self.dd_p=ft.Dropdown(width=102,options=[ft.DropdownOption(key="AM",text="AM"),ft.DropdownOption(key="PM",text="PM")],
                              value="PM",disabled=True,**dds)
        self.dd_h.border_color=ACCENT2; self.dd_m.border_color=ACCENT2; self.dd_p.border_color=ACCENT2
        self.dd_h.focused_border_color=ACCENT2; self.dd_m.focused_border_color=ACCENT2; self.dd_p.focused_border_color=ACCENT2
        self.dd_h.color=TXT_MUTED; self.dd_m.color=TXT_MUTED; self.dd_p.color=TXT_MUTED

    def _buscar(self,e):
        tel=self.tf_tel.value.strip()
        if not tel: return
        r=buscar_cliente(tel)
        if r: self.tf_dom.value,self.tf_cru.value=r; self.state.cli_existe=True
        else: self.state.cli_existe=False
        self.page.update()

    def _toggle_tel(self,e):
        off="no" in self.seg_tel.selected
        self.tf_tel.disabled=off; self.page.update()

    def _toggle_hora(self,e):
        off="no" in self.seg_hora.selected
        for dd in (self.dd_h,self.dd_m,self.dd_p):
            dd.disabled=off
            dd.border_color=ACCENT2 if off else ACCENT
            dd.focused_border_color=ACCENT2 if off else ACCENT
            dd.color=TXT_MUTED if off else TXT
        self.page.update()

    def get_hora_str(self):
        if "no" in self.seg_hora.selected: return ""
        return f"{self.dd_h.value}:{self.dd_m.value} {self.dd_p.value}"

    def get_tel(self):
        if "no" in self.seg_tel.selected: return ""
        return self.tf_tel.value.strip()

    def limpiar(self):
        self.tf_dom.value=""; self.tf_cru.value=""; self.tf_tel.value=""
        self.seg_tel.selected=["si"]; self.seg_hora.selected=["no"]
        self.tf_tel.disabled=False
        self.dd_h.disabled=True; self.dd_m.disabled=True; self.dd_p.disabled=True
        self.dd_h.border_color=ACCENT2; self.dd_m.border_color=ACCENT2; self.dd_p.border_color=ACCENT2
        self.dd_h.focused_border_color=ACCENT2; self.dd_m.focused_border_color=ACCENT2; self.dd_p.focused_border_color=ACCENT2
        self.dd_h.color=TXT_MUTED; self.dd_m.color=TXT_MUTED; self.dd_p.color=TXT_MUTED
        self.dd_h.value="12"; self.dd_m.value="00"; self.dd_p.value="PM"

    def cargar_desde_pedido(self,pedido):
        self.tf_dom.value=str(pedido.get("domicilio",""))
        self.tf_cru.value=str(pedido.get("cruces",""))
        tel=str(pedido.get("telefono","")).strip()
        self.tf_tel.value=tel
        if tel:
            self.seg_tel.selected=["si"]
            self.tf_tel.disabled=False
        else:
            self.seg_tel.selected=["no"]
            self.tf_tel.disabled=True

        hora=str(pedido.get("hora_especifica","")).strip()
        if hora:
            self.seg_hora.selected=["si"]
            partes=hora.split()
            if len(partes)==2 and ":" in partes[0]:
                hh,mm=partes[0].split(":",1)
                if hh and mm:
                    self.dd_h.value=hh
                    self.dd_m.value=mm
                if partes[1] in ("AM","PM"):
                    self.dd_p.value=partes[1]
        else:
            self.seg_hora.selected=["no"]
            self.dd_h.value="12"; self.dd_m.value="00"; self.dd_p.value="PM"

        off="no" in self.seg_hora.selected
        for dd in (self.dd_h,self.dd_m,self.dd_p):
            dd.disabled=off
            dd.border_color=ACCENT2 if off else ACCENT
            dd.focused_border_color=ACCENT2 if off else ACCENT
            dd.color=TXT_MUTED if off else TXT

    def build(self):
        def lbl_ico(icon,text,width=110):
            return ft.Container(
                content=ft.Row([
                    ft.Text(icon,size=15),
                    ft.Text(text,color=GOLD,size=12,weight=ft.FontWeight.BOLD),
                ],spacing=6,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                width=width,
            )
        section_header=ft.Row([
            ft.Container(
                content=ft.Text("👤",size=16),
                width=32,height=32,
                bgcolor=SURFACE_HIGH,
                border_radius=16,
                alignment=ft.Alignment(0,0),
                border=ft.Border.all(1,ACCENT_SOFT),
            ),
            ft.Column([
                ft.Text("Datos del cliente",size=14,weight=ft.FontWeight.W_900,color=GOLD),
                ft.Text("Información para entrega y contacto",size=10,color=TXT_MUTED),
            ],spacing=0),
        ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER)
        primer_paso=ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ARROW_BACK,color=ACCENT,size=14),
                ft.Text("Primer paso",size=11,color=ACCENT,weight=ft.FontWeight.BOLD),
            ],spacing=4,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#FFF3E5",
            border=ft.Border.all(1,ACCENT_SOFT),
            border_radius=14,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=4,
                color=SHADOW_BLACK_LIGHT,
                offset=ft.Offset(0,1),
            ),
            padding=ft.Padding(10,4,10,4),
        )
        return ft.Container(
            content=ft.Column([
                section_header,
                ft.Divider(color=DIVIDER_SOFT,height=1),
                ft.Row([lbl_ico("🏠","Domicilio:"),self.tf_dom],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    lbl_ico("📞","Teléfono:"),
                    self.seg_tel,
                    self.tf_tel,
                    primer_paso,
                ],spacing=6,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([lbl_ico("🧭","Cruces:"),self.tf_cru],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.Column([lbl_ico("⏰","Hora:"),ft.Container(height=13)],spacing=2,horizontal_alignment=ft.CrossAxisAlignment.START),
                    ft.Column([self.seg_hora,ft.Container(height=13)],spacing=2,horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Column([self.dd_h,ft.Text("Hora",size=11,color=ACCENT,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=2),
                    ft.Column([self.dd_m,ft.Text("Minutos",size=11,color=ACCENT,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=2),
                    ft.Column([self.dd_p,ft.Text("AM/PM",size=11,color=ACCENT,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=2),
                ],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],spacing=10),
            bgcolor=BG_CARD,
            border_radius=14,
            padding=14,
            border=ft.Border.all(1,ACCENT_SOFT),
            shadow=ft.BoxShadow(spread_radius=0,blur_radius=8,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,2)))


class MenuProductos:
    def __init__(self,on_product_click):
        self.on_click=on_product_click

    def _subtitle(self,categoria,name):
        if categoria=="Comida":
            return {
                "Torta":"Opciones: Carne, Buche, Lengua, Mixta",
                "Torta Mini":"Opciones: Carne, Buche, Lengua, Mixta",
                "Taco Dorado":"Opciones: Papa, Frijol, Requesón, Picadillo",
                "Taco c/Carne":"Opciones: Tipo de taco y carne",
                "Kilo de Carne":"Opciones: Tipo de carne y cantidad",
                "Crear Producto":"Temporal: define nombre y precio",
            }.get(name,"")
        if categoria=="Bebidas":
            return {
                "Refresco":"Opciones: Coca, Fanta, Manzana, Sprite",
                "Cerveza":"Opciones: Clara u Obscura",
                "Agua Fresca 500ml":"Opciones: Jamaica u Horchata",
                "Agua Fresca 1LT":"Opciones: Jamaica u Horchata",
                "Caguama":"Presentación: Caguama",
            }.get(name,"")
        if categoria=="Paquetes":
            return {
                "Paquete #1":"Incluye: Torta, Tacos y Bebida",
                "Paquete #2":"Incluye: Torta, Tacos y Bebida",
            }.get(name,"")
        return ""

    def _card(self,name,price,color,width,height,name_size,price_size,subtitle,subtitle_size):
        icon=PRODUCT_ICONS.get(name,"🍽️")
        # Badge circular con icono visual (compacto)
        icon_badge=ft.Container(
            content=ft.Text(icon,size=20,text_align=ft.TextAlign.CENTER),
            width=36,height=36,
            bgcolor=SURFACE_HIGH,
            border_radius=18,
            alignment=ft.Alignment(0,0),
            border=ft.Border.all(1,ACCENT_SOFT),
            shadow=ft.BoxShadow(spread_radius=0,blur_radius=3,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,1)),
        )
        # Bloque de precio con pill
        price_pill=ft.Container(
            content=ft.Text(f"${price}",size=price_size-3,weight=ft.FontWeight.W_900,color="white",text_align=ft.TextAlign.CENTER),
            bgcolor=ACCENT,
            border_radius=10,
            padding=ft.Padding(7,1,7,1),
            alignment=ft.Alignment(0,0),
        )
        body=ft.Row([
            icon_badge,
            ft.Container(
                content=ft.Column([
                    ft.Text(name,size=name_size,weight=ft.FontWeight.W_800,color=TXT,
                            max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row([price_pill],alignment=ft.MainAxisAlignment.START),
                ],spacing=3,alignment=ft.MainAxisAlignment.CENTER,horizontal_alignment=ft.CrossAxisAlignment.START),
                expand=True,
                padding=ft.Padding(6,0,0,0),
            ),
        ],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER)
        return ft.Container(
            content=body,
            width=width,height=height,bgcolor=color,border_radius=12,
            padding=ft.Padding(7,5,7,5),
            border=ft.Border.all(1,ACCENT_SOFT),
            on_click=lambda _,n=name,p=price: self.on_click(n,p),ink=True,
            shadow=ft.BoxShadow(spread_radius=0,blur_radius=5,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,2)))

    def _grid(self,categoria,items,color,runs_count,card_w,card_h,name_size,price_size,subtitle_size,ratio):
        g=ft.GridView(
            runs_count=runs_count,
            child_aspect_ratio=ratio,
            spacing=10,
            run_spacing=10,
            padding=10,
            expand=True,
        )
        for n,p in items:
            g.controls.append(
                self._card(
                    n,
                    p,
                    color,
                    card_w,
                    card_h,
                    name_size,
                    price_size,
                    self._subtitle(categoria,n),
                    subtitle_size,
                )
            )
        return g

    def build(self):
        cats=list(MENU.keys())
        cfg={
            "Comida":{"runs":3,"w":160,"h":58,"name":12,"price":15,"sub":9,"ratio":2.7},
            "Paquetes":{"runs":3,"w":160,"h":58,"name":12,"price":15,"sub":9,"ratio":2.7},
            "Bebidas":{"runs":3,"w":160,"h":58,"name":12,"price":15,"sub":9,"ratio":2.7},
        }
        return ft.Tabs(
            content=ft.Column([
                ft.Container(
                    content=ft.TabBar(
                        tabs=[ft.Tab(label=f"{CATEGORY_ICONS[c]}  {c}") for c in cats],
                        indicator_color=ACCENT,
                        label_color=GOLD,
                        unselected_label_color=TXT_MUTED,
                    ),
                    bgcolor=SURFACE_HIGH,
                    border_radius=12,
                    border=ft.Border.all(1,ACCENT_SOFT),
                ),
                ft.TabBarView(
                    controls=[
                        self._grid(
                            c,
                            MENU[c],
                            GRID_COLORS[c],
                            cfg[c]["runs"],
                            cfg[c]["w"],
                            cfg[c]["h"],
                            cfg[c]["name"],
                            cfg[c]["price"],
                            cfg[c]["sub"],
                            cfg[c]["ratio"],
                        ) for c in cats
                    ],
                    expand=True,
                ),
            ],expand=True,spacing=6),length=len(cats),selected_index=0,expand=True)

# Colores por bebida
DRINK_COLORS={"Coca":"#8b0000","Fanta":"#cc5500","Manzana":"#8B6914","Sprite":"#2d6e2d","Jamaica":"#722F37","Horchata":"#c8b89a","Clara":"#c8a951","Obscura":"#3b1f0b"}

class ItemDialog:
    """Ventana de selección de variantes para productos."""
    def __init__(self,page,on_accept):
        self.page=page; self.on_accept=on_accept

    def _hero_header(self,name,price,subtitle=""):
        icon=PRODUCT_ICONS.get(name,"🍽️")
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(icon,size=34,text_align=ft.TextAlign.CENTER),
                    width=64,height=64,
                    bgcolor=SURFACE_HIGH,
                    border_radius=32,
                    alignment=ft.Alignment(0,0),
                    border=ft.Border.all(2,HIGHLIGHT),
                    shadow=ft.BoxShadow(spread_radius=0,blur_radius=6,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,2)),
                ),
                ft.Column([
                    ft.Text(name,size=18,weight=ft.FontWeight.W_900,color="white"),
                    ft.Text(subtitle if subtitle else f"Configura tu {name.lower()}",size=11,color=ft.Colors.with_opacity(0.85,"white")),
                ],spacing=2,alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Text(f"${price}",size=18,weight=ft.FontWeight.W_900,color="white"),
                    bgcolor=ft.Colors.with_opacity(0.22,"white"),
                    border_radius=14,
                    padding=ft.Padding(14,6,14,6),
                ) if price is not None else ft.Container(),
            ],spacing=12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ACCENT,
            padding=ft.Padding(16,12,16,12),
            border_radius=ft.BorderRadius(top_left=14,top_right=14,bottom_left=0,bottom_right=0),
        )

    def _toggle_btns(self,options,selected,max_sel=None):
        btns=[]
        for opt in options:
            c=ft.Container(
                content=ft.Text(opt,color=TXT,size=15,weight=ft.FontWeight.W_700,text_align=ft.TextAlign.CENTER),
                bgcolor=BG_ITEM,border=ft.Border.all(1.5,ACCENT_SOFT),border_radius=12,
                width=145,height=48,alignment=ft.Alignment(0,0),data=opt,ink=True,
                shadow=ft.BoxShadow(spread_radius=0,blur_radius=3,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,1)),
                on_click=lambda e,s=selected,mx=max_sel: self._toggle(e,s,mx))
            btns.append(c)
        return btns

    def _toggle(self,e,selected,max_sel):
        opt=e.control.data
        if opt in selected:
            selected.discard(opt)
            e.control.bgcolor=BG_ITEM; e.control.border=ft.Border.all(1.5,ACCENT_SOFT)
            e.control.content.color=TXT
        else:
            if max_sel and len(selected)>=max_sel: return
            selected.add(opt)
            e.control.bgcolor=ACCENT; e.control.border=ft.Border.all(2,ACCENT_DARK)
            e.control.content.color="white"
        self.page.update()

    def _multiplier(self):
        qty=[1]
        txt=ft.Text("1",size=22,color=TXT,weight=ft.FontWeight.W_900,width=50,text_align=ft.TextAlign.CENTER)
        def minus(_):
            if qty[0]>1: qty[0]-=1; txt.value=str(qty[0]); self.page.update()
        def plus(_):
            qty[0]+=1; txt.value=str(qty[0]); self.page.update()
        def circle_btn(icon,color,fn):
            return ft.Container(
                content=ft.Icon(icon,color="white",size=22),
                width=44,height=44,
                bgcolor=color,
                border_radius=22,
                alignment=ft.Alignment(0,0),
                on_click=fn,ink=True,
                shadow=ft.BoxShadow(spread_radius=0,blur_radius=4,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,2)),
            )
        row=ft.Row([
            circle_btn(ft.Icons.REMOVE,ACCENT,minus),
            ft.Container(
                content=txt,
                bgcolor=SURFACE_HIGH,
                border_radius=12,
                padding=ft.Padding(18,8,18,8),
                border=ft.Border.all(1.5,ACCENT_SOFT),
                shadow=ft.BoxShadow(spread_radius=0,blur_radius=3,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,1)),
            ),
            circle_btn(ft.Icons.ADD,GREEN,plus),
        ],alignment=ft.MainAxisAlignment.CENTER,spacing=12)
        return row,qty

    def _section(self,title,controls):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(width=4,height=16,bgcolor=ACCENT,border_radius=2),
                    ft.Text(title,color=GOLD,size=13,weight=ft.FontWeight.W_900),
                ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row(controls,wrap=True,spacing=10,run_spacing=10,alignment=ft.MainAxisAlignment.CENTER),
            ],spacing=8),
            bgcolor=BG_PANEL,
            padding=ft.Padding(12,10,12,12),
            border_radius=12,
            border=ft.Border.all(1,ACCENT_SOFT),
        )

    def _drink_btns(self,options,selected,max_sel=None):
        btns=[]
        drink_emojis={"Coca":"🥤","Fanta":"🧃","Manzana":"🧃","Sprite":"🧃","Jamaica":"🌺","Horchata":"🥛","Clara":"🍺","Obscura":"🍺"}
        for opt in options:
            bg=DRINK_COLORS.get(opt,BG_ITEM)
            emoji=drink_emojis.get(opt,"🥤")
            c=ft.Container(
                content=ft.Row([
                    ft.Text(emoji,size=18),
                    ft.Text(opt,color="white",size=13,weight=ft.FontWeight.W_800,text_align=ft.TextAlign.CENTER),
                ],spacing=6,alignment=ft.MainAxisAlignment.CENTER,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=bg,border=ft.Border.all(1.5,ACCENT_SOFT),border_radius=12,
                width=135,height=46,alignment=ft.Alignment(0,0),data=f"{opt}|{bg}",ink=True,
                shadow=ft.BoxShadow(spread_radius=0,blur_radius=3,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,1)),
                on_click=lambda e,s=selected,mx=max_sel: self._drink_toggle(e,s,mx))
            btns.append(c)
        return btns

    def _drink_toggle(self,e,selected,max_sel):
        parts=e.control.data.split("|")
        opt=parts[0]; orig_bg=parts[1]
        if opt in selected:
            selected.discard(opt)
            e.control.bgcolor=orig_bg; e.control.border=ft.Border.all(1.5,ACCENT_SOFT)
        else:
            if max_sel and len(selected)>=max_sel:
                # Deselect previous
                for s in list(selected): selected.discard(s)
                for c in e.control.parent.controls:
                    if hasattr(c,'data') and c.data:
                        p=c.data.split("|")
                        if len(p)==2: c.bgcolor=p[1]; c.border=ft.Border.all(1.5,ACCENT_SOFT)
            selected.add(opt)
            e.control.bgcolor=ft.Colors.with_opacity(0.25,"white"); e.control.border=ft.Border.all(3,"white")
        self.page.update()

    def _close_dlg(self,dlg):
        dlg.open=False; self.page.update()

    def _warn(self):
        self.page.snack_bar=ft.SnackBar(ft.Text("Seleccionar por lo menos 1 opción",color="white"),bgcolor=ACCENT)
        self.page.snack_bar.open=True; self.page.update()

    def _accept_btn(self,on_click,dlg=None):
        accept=ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE,color="white",size=18),
                ft.Text("Aceptar",color="white",size=14,weight=ft.FontWeight.W_900),
            ],spacing=8,alignment=ft.MainAxisAlignment.CENTER,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=GREEN,
            border_radius=12,
            padding=ft.Padding(20,10,20,10),
            on_click=on_click,ink=True,
            shadow=ft.BoxShadow(spread_radius=0,blur_radius=6,color=SHADOW_BLACK_MED,offset=ft.Offset(0,3)),
        )
        controls=[]
        if dlg is not None:
            cancel=ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CLOSE,color=TXT_MUTED,size=16),
                    ft.Text("Cancelar",color=TXT_MUTED,size=14,weight=ft.FontWeight.W_700),
                ],spacing=6,alignment=ft.MainAxisAlignment.CENTER,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=SURFACE_HIGH,
                border_radius=12,
                padding=ft.Padding(18,10,18,10),
                border=ft.Border.all(1,ACCENT_SOFT),
                on_click=lambda _: self._close_dlg(dlg),ink=True,
            )
            controls.append(cancel)
        controls.append(accept)
        return ft.Row(controls,alignment=ft.MainAxisAlignment.CENTER,spacing=10)

    def show(self,name,price):
        if name in ("Torta","Torta Mini"): self._show_meat(name,price,2)
        elif name=="Taco Dorado": self._show_taco_dorado(name,price)
        elif name=="Taco c/Carne": self._show_taco_carne(name,price)
        elif name=="Kilo de Carne": self._show_kilo(name,price)
        elif name=="Crear Producto": self._show_custom_product()
        elif name in ("Paquete #1","Paquete #2"): self._show_paq12(name,price)
        elif name in ("Paquete #3","Paquete #4","Paquete #5"): self._show_simple(name,price)
        elif name=="Refresco": self._show_sel(name,price,"🥤","Tipo de refresco:",REFRESCO_TYPES)
        elif name=="Cerveza": self._show_sel(name,price,"🍺","Tipo de cerveza:",BEER_TYPES)
        elif name in ("Agua Fresca 500ml","Agua Fresca 1LT"): self._show_sel(name,price,"🥤","Tipo de agua fresca:",AGUA_TYPES)
        elif name=="Caguama": self._show_simple(name,price)

    def _show_custom_product(self):
        mul,qty=self._multiplier()
        tf_n=ft.TextField(
            label="Nombre del producto",
            dense=True,
            width=300,
            text_size=14,
            color=TXT,
            border_color=ACCENT2,
            focused_border_color=ACCENT,
        )
        tf_p=ft.TextField(
            label="Precio",
            dense=True,
            width=180,
            text_size=14,
            color=TXT,
            border_color=ACCENT2,
            focused_border_color=ACCENT,
            suffix=ft.Text("$"),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        dlg=ft.AlertDialog(
            bgcolor=BG_CARD,
            title=self._hero_header("Crear Producto",None,"Producto temporal solo para este pedido"),
            title_padding=ft.Padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        def accept(_):
            nombre=tf_n.value.strip()
            precio_txt=(tf_p.value or "").strip().replace(",",".")
            if not nombre or not precio_txt:
                self.page.snack_bar=ft.SnackBar(ft.Text("Captura nombre y precio",color="white"),bgcolor=ACCENT)
                self.page.snack_bar.open=True; self.page.update()
                return
            try:
                precio=float(precio_txt)
            except ValueError:
                self.page.snack_bar=ft.SnackBar(ft.Text("Precio inválido",color="white"),bgcolor=ACCENT)
                self.page.snack_bar.open=True; self.page.update()
                return
            if precio<=0:
                self.page.snack_bar=ft.SnackBar(ft.Text("El precio debe ser mayor a 0",color="white"),bgcolor=ACCENT)
                self.page.snack_bar.open=True; self.page.update()
                return
            if precio.is_integer(): precio=int(precio)
            self.on_accept(nombre,precio,qty[0],"")
            self._close_dlg(dlg)
        dlg.content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE,color=TXT_MUTED,size=14),
                    ft.Text("Este producto se agrega solo al pedido actual.",color=TXT_MUTED,size=11,italic=True),
                ],spacing=6),
                bgcolor=BG_PANEL,
                padding=ft.Padding(10,8,10,8),
                border_radius=10,
            ),
            tf_n,
            tf_p,
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(width=4,height=16,bgcolor=ACCENT,border_radius=2),
                        ft.Text("Multiplicador",color=GOLD,size=13,weight=ft.FontWeight.W_900),
                    ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    mul,
                ],spacing=8),
                bgcolor=BG_PANEL,
                padding=ft.Padding(12,10,12,12),
                border_radius=12,
                border=ft.Border.all(1,ACCENT_SOFT),
            ),
            self._accept_btn(accept,dlg),
        ],spacing=10,tight=True,width=360)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _qty_section(self,mul):
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(width=4,height=16,bgcolor=ACCENT,border_radius=2),
                    ft.Text("Cantidad",color=GOLD,size=13,weight=ft.FontWeight.W_900),
                ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                mul,
            ],spacing=8),
            bgcolor=BG_PANEL,
            padding=ft.Padding(12,10,12,12),
            border_radius=12,
            border=ft.Border.all(1,ACCENT_SOFT),
        )

    def _show_meat(self,name,price,max_sel):
        sel=set(); btns=self._toggle_btns(MEAT_TYPES,sel,max_sel=max_sel)
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,
            title=self._hero_header(name,price,f"Selecciona hasta {max_sel} tipo(s) de carne"),
            title_padding=ft.Padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=14))
        def accept(_):
            if not sel: self._warn(); return
            self.on_accept(name,price,qty[0],", ".join(sorted(sel))); self._close_dlg(dlg)
        dlg.content=ft.Column([
            self._section("Tipo de carne (máx 2)" if max_sel==2 else "Tipo de carne",btns),
            self._qty_section(mul),
            self._accept_btn(accept,dlg)
        ],spacing=12,tight=True,width=380)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_taco_dorado(self,name,price):
        sel=set(); btns=self._toggle_btns(TACO_TYPES,sel)
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,
            title=self._hero_header(name,price,"Elige los rellenos"),
            title_padding=ft.Padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=14))
        def accept(_):
            if not sel: self._warn(); return
            self.on_accept(name,price,qty[0],", ".join(sorted(sel))); self._close_dlg(dlg)
        dlg.content=ft.Column([
            self._section("Tipo de taco",btns),
            self._qty_section(mul),
            self._accept_btn(accept,dlg)
        ],spacing=12,tight=True,width=380)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_taco_carne(self,name,price):
        sel_t=set(); btns_t=self._toggle_btns(TACO_TYPES,sel_t)
        sel_m=set(); btns_m=self._toggle_btns(MEAT_TYPES,sel_m)
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,
            title=self._hero_header(name,price,"Elige tipo de taco y carne"),
            title_padding=ft.Padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=14))
        def accept(_):
            if not sel_t or not sel_m: self._warn(); return
            v=f"Taco: {', '.join(sorted(sel_t))} | Carne: {', '.join(sorted(sel_m))}"
            self.on_accept(name,price,qty[0],v); self._close_dlg(dlg)
        dlg.content=ft.Column([
            self._section("Tipo de taco",btns_t),
            self._section("Tipo de carne",btns_m),
            self._qty_section(mul),
            self._accept_btn(accept,dlg)
        ],spacing=12,tight=True,width=400)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_kilo(self,name,price):
        sel=set(); btns=self._toggle_btns(MEAT_TYPES,sel,max_sel=1)
        mul,qty=self._multiplier()
        mode=["gramos"]
        tf_g=ft.TextField(value="",width=130,dense=True,text_size=14,color=TXT,border_color=ACCENT_SOFT,focused_border_color=ACCENT,suffix=ft.Text("g"),keyboard_type=ft.KeyboardType.NUMBER)
        tf_d=ft.TextField(value="",width=130,dense=True,text_size=14,color=TXT,border_color=ACCENT_SOFT,focused_border_color=ACCENT,suffix=ft.Text("$"),keyboard_type=ft.KeyboardType.NUMBER,disabled=True)
        seg=ft.SegmentedButton(segments=[ft.Segment(value="gramos",label=ft.Text("⚖️ Gramos")),ft.Segment(value="dinero",label=ft.Text("💵 Dinero"))],
            selected=["gramos"],allow_empty_selection=False,on_change=lambda e: _mc(e))
        def _mc(e):
            mode[0]=list(seg.selected)[0]; tf_g.disabled=(mode[0]!="gramos"); tf_d.disabled=(mode[0]!="dinero"); tf_g.value=""; tf_d.value=""; self.page.update()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,
            title=self._hero_header(name,price,"Selecciona carne y cantidad"),
            title_padding=ft.Padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=14))
        def accept(_):
            if not sel: self._warn(); return
            try:
                if mode[0]=="gramos": g=int(tf_g.value); d=round(g*300/1000)
                else: d=int(tf_d.value); g=round(d*1000/300)
            except: self._warn(); return
            if g<=0 and d<=0: return
            v=f"{', '.join(sel)} - {g}g (${d})"
            self.on_accept(name,d,qty[0],v); self._close_dlg(dlg)
        cant_box=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(width=4,height=16,bgcolor=ACCENT,border_radius=2),
                    ft.Text("Cantidad por gramos o dinero",color=GOLD,size=13,weight=ft.FontWeight.W_900),
                ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                seg,
                ft.Row([
                    ft.Column([ft.Text("Gramos",color=TXT_MUTED,size=11,weight=ft.FontWeight.W_600),tf_g],spacing=4),
                    ft.Column([ft.Text("Dinero",color=TXT_MUTED,size=11,weight=ft.FontWeight.W_600),tf_d],spacing=4),
                ],spacing=16),
            ],spacing=10),
            bgcolor=BG_PANEL,
            padding=ft.Padding(12,10,12,12),
            border_radius=12,
            border=ft.Border.all(1,ACCENT_SOFT),
        )
        mul_box=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(width=4,height=16,bgcolor=ACCENT,border_radius=2),
                    ft.Text("Multiplicador",color=GOLD,size=13,weight=ft.FontWeight.W_900),
                ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                mul,
            ],spacing=8),
            bgcolor=BG_PANEL,
            padding=ft.Padding(12,10,12,12),
            border_radius=12,
            border=ft.Border.all(1,ACCENT_SOFT),
        )
        dlg.content=ft.Column([
            self._section("Tipo de carne",btns),
            cant_box,
            mul_box,
            self._accept_btn(accept,dlg)
        ],spacing=10,tight=True,width=420)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_paq12(self,name,price):
        sel_m=set(); btns_m=self._toggle_btns(MEAT_TYPES,sel_m,max_sel=2)
        sel_t=set(); btns_t=self._toggle_btns(TACO_TYPES,sel_t)
        sel_d=set(); btns_d=self._drink_btns(DRINK_TYPES,sel_d,max_sel=1)
        sel_b=set(); btns_beer=self._drink_btns(BEER_TYPES,sel_b,max_sel=1)
        use_beer=[False]
        beer_toggle=ft.SegmentedButton(
            segments=[ft.Segment(value="refresco",label=ft.Text("🥤 Refresco")),ft.Segment(value="cerveza",label=ft.Text("🍺 Cerveza +$5"))],
            selected=["refresco"],allow_empty_selection=False,on_change=lambda e: _bt(e))
        drink_row=ft.Row(btns_d,wrap=True,spacing=8,run_spacing=8,alignment=ft.MainAxisAlignment.CENTER)
        beer_row=ft.Row(btns_beer,wrap=True,spacing=8,run_spacing=8,alignment=ft.MainAxisAlignment.CENTER,visible=False)
        def _bt(e):
            v=list(beer_toggle.selected)[0]; use_beer[0]=(v=="cerveza")
            drink_row.visible=not use_beer[0]; beer_row.visible=use_beer[0]
            sel_d.clear(); sel_b.clear()
            for b in btns_d:
                p=b.data.split("|"); b.bgcolor=p[1]; b.border=ft.Border.all(1.5,ACCENT_SOFT)
            for b in btns_beer:
                p=b.data.split("|"); b.bgcolor=p[1]; b.border=ft.Border.all(1.5,ACCENT_SOFT)
            self.page.update()
        mul,qty=self._multiplier()
        col_left=ft.Column([self._section("Carne de torta (máx 2)",btns_m),self._section("Tipo de tacos",btns_t)],spacing=12,expand=True)
        bebida_box=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(width=4,height=16,bgcolor=ACCENT,border_radius=2),
                    ft.Text("Bebida",color=GOLD,size=13,weight=ft.FontWeight.W_900),
                ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                beer_toggle,
                drink_row,
                beer_row,
            ],spacing=10),
            bgcolor=BG_PANEL,
            padding=ft.Padding(12,10,12,12),
            border_radius=12,
            border=ft.Border.all(1,ACCENT_SOFT),
        )
        col_right=ft.Column([bebida_box],spacing=10,expand=True)
        dlg=ft.AlertDialog(bgcolor=BG_CARD,
            title=self._hero_header(name,price,"Configura tu paquete completo"),
            title_padding=ft.Padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=14))
        def accept(_):
            if not sel_m or not sel_t: self._warn(); return
            if use_beer[0] and not sel_b: self._warn(); return
            if not use_beer[0] and not sel_d: self._warn(); return
            fp=price+5 if use_beer[0] else price
            beb=f"Cerveza {', '.join(sel_b)}" if use_beer[0] else ", ".join(sorted(sel_d))
            v=f"Torta: {', '.join(sorted(sel_m))} | Tacos: {', '.join(sorted(sel_t))} | Bebida: {beb}"
            self.on_accept(name,fp,qty[0],v); self._close_dlg(dlg)
        dlg.content=ft.Column([
            ft.Row([col_left,ft.VerticalDivider(color=DIVIDER_SOFT,width=1),col_right],spacing=14,vertical_alignment=ft.CrossAxisAlignment.START),
            self._qty_section(mul),
            self._accept_btn(accept,dlg)
        ],spacing=12,tight=True,width=780,height=560)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_simple(self,name,price):
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,
            title=self._hero_header(name,price,"Selecciona la cantidad"),
            title_padding=ft.Padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=14))
        def accept(_):
            self.on_accept(name,price,qty[0],""); self._close_dlg(dlg)
        dlg.content=ft.Column([
            self._qty_section(mul),
            self._accept_btn(accept,dlg)
        ],spacing=12,tight=True,width=320)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_sel(self,name,price,ico,label,options):
        is_drink=any(o in DRINK_COLORS for o in options)
        sel=set()
        btns=self._drink_btns(options,sel,max_sel=1) if is_drink else self._toggle_btns(options,sel,max_sel=1)
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,
            title=self._hero_header(name,price,label.rstrip(":")),
            title_padding=ft.Padding.all(0),
            shape=ft.RoundedRectangleBorder(radius=14))
        def accept(_):
            if not sel: self._warn(); return
            self.on_accept(name,price,qty[0],", ".join(sel)); self._close_dlg(dlg)
        dlg.content=ft.Column([
            self._section(label.rstrip(":"),btns),
            self._qty_section(mul),
            self._accept_btn(accept,dlg)
        ],spacing=12,tight=True,width=400)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()


class ResumenPedido:
    """Panel derecho: selector de plato, resumen con drag & drop, total."""
    def __init__(self,page,state):
        self.page=page; self.state=state
        self._drag_map={}  # drag_key -> (plato_idx, item_idx)
        self.dd_plato=ft.Dropdown(label="Plato actual",dense=True,text_size=12,
                                  on_select=self._on_plato_change,
                                  width=160,
                                  border_color=ACCENT_SOFT,
                                  focused_border_color=ACCENT,
                                  color=TXT,
                                  bgcolor=SURFACE_HIGH,
                                  filled=True)
        self.lv_content=ft.Column(
            spacing=4,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            alignment=ft.MainAxisAlignment.START,
        )
        self.lv=ft.Container(
            content=self.lv_content,
            expand=True,
            padding=0,
            alignment=ft.Alignment(-1, -1),
        )
        self.txt_total=ft.Text("$0",size=24,weight=ft.FontWeight.W_900,color="white")
        self._editing_idx=-1  # plato being renamed

    def _on_plato_change(self,e):
        v=self.dd_plato.value
        if v is not None and v.isdigit(): self.state.activo=int(v)

    def refresh(self):
        self._drag_map.clear(); self.lv_content.controls.clear()
        # Refresh dropdown
        self.dd_plato.options=[ft.DropdownOption(key=str(i),text=p.nombre) for i,p in enumerate(self.state.platos)]
        if 0<=self.state.activo<len(self.state.platos): self.dd_plato.value=str(self.state.activo)
        elif self.state.platos: self.dd_plato.value="0"; self.state.activo=0
        else: self.dd_plato.value=None

        for pi,plato in enumerate(self.state.platos):
            is_active=(pi==self.state.activo)
            # Build items column
            items_col=ft.Column(spacing=4)
            if not plato.items:
                items_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.SHOPPING_BASKET_OUTLINED,color=TXT_MUTED,size=14),
                            ft.Text("Sin productos aún",color=TXT_MUTED,size=11,italic=True),
                        ],spacing=6,alignment=ft.MainAxisAlignment.CENTER),
                        padding=ft.Padding(0,8,0,8),
                    )
                )
            for ii,item in enumerate(plato.items):
                dk=f"{pi}:{ii}"
                self._drag_map[dk]={"sp":pi,"si":ii}
                sub=item["price"]*item["qty"]
                vr=item.get("variant","")
                ico=PRODUCT_ICONS.get(item["name"],"🍽️")
                name_col=ft.Column([ft.Text(item["name"],color=TXT,size=15,weight=ft.FontWeight.W_800)],spacing=2)
                if vr: name_col.controls.append(ft.Text(f"→ {vr}",color=GOLD,size=12,weight=ft.FontWeight.W_500))
                qty_pill=ft.Container(
                    content=ft.Text(f'{item["qty"]}x',color="white",weight=ft.FontWeight.W_900,size=12),
                    bgcolor=ACCENT,
                    border_radius=10,
                    padding=ft.Padding(8,2,8,2),
                )
                icon_box=ft.Container(
                    content=ft.Text(ico,size=16),
                    width=30,height=30,
                    bgcolor=SURFACE_HIGH,
                    border_radius=15,
                    alignment=ft.Alignment(0,0),
                    border=ft.Border.all(1,ACCENT_SOFT),
                )
                item_row=ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DRAG_INDICATOR,color=ACCENT_SOFT,size=14),
                        icon_box,
                        qty_pill,
                        ft.Container(content=name_col,expand=True),
                        ft.Text(f'${sub}',color=GOLD,weight=ft.FontWeight.W_900,size=15),
                        ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,icon_color=ACCENT,icon_size=16,
                                      data=f"{pi}:{ii}",on_click=self._quitar,padding=0,tooltip="Quitar uno"),
                    ],spacing=6,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=SURFACE_HIGH,
                    border_radius=10,
                    padding=ft.Padding(8,6,8,6),
                    border=ft.Border.all(1,ACCENT_SOFT),
                )
                draggable=ft.Draggable(content=item_row,group="items",data=dk)
                items_col.controls.append(draggable)

            # Plato header
            if self._editing_idx==pi:
                name_ctl=ft.TextField(value=plato.nombre,dense=True,height=38,text_size=17,
                                      color=TXT,width=180,border_color=ACCENT,
                                      on_submit=lambda e,idx=pi: self._rename_done(e,idx))
            else:
                name_ctl=ft.Row([
                    ft.Container(
                        content=ft.Text(f"#{pi+1}",color="white",size=11,weight=ft.FontWeight.W_900),
                        bgcolor=ACCENT if is_active else TXT_MUTED,
                        border_radius=10,
                        padding=ft.Padding(7,2,7,2),
                    ),
                    ft.Text(plato.nombre,color=GOLD,weight=ft.FontWeight.W_900,size=18),
                    ft.Container(
                        content=ft.Text("activo",color=GREEN,size=10,weight=ft.FontWeight.W_700),
                        bgcolor=ft.Colors.with_opacity(0.15,GREEN),
                        border_radius=8,
                        padding=ft.Padding(6,2,6,2),
                    ) if is_active else ft.Container(),
                ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER)

            dup_btn=ft.Container(
                content=ft.Text("Duplicar Plato",color="white",size=10,weight=ft.FontWeight.W_800),
                bgcolor=GREEN,
                border_radius=8,
                padding=ft.Padding(8,4,8,4),
                data=pi,
                on_click=self._dup,
                ink=True,
                tooltip="Duplicar este plato",
            )
            header=ft.Row([
                name_ctl,ft.Row([
                    ft.IconButton(icon=ft.Icons.EDIT,icon_color=GOLD,icon_size=16,data=pi,on_click=self._edit_name,padding=0,tooltip="Renombrar"),
                    dup_btn,
                    ft.IconButton(icon=ft.Icons.DELETE,icon_color=ACCENT,icon_size=16,data=pi,on_click=self._del,padding=0,tooltip="Eliminar"),
                ],spacing=4,vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            plato_box=ft.Container(
                content=ft.Column([header,items_col],spacing=8),
                bgcolor=BG_PANEL,border_radius=12,padding=10,
                margin=ft.Margin(bottom=8),
                border=ft.Border.all(2 if is_active else 1, ACCENT if is_active else ACCENT_SOFT),
                shadow=ft.BoxShadow(spread_radius=0,blur_radius=4 if is_active else 2,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,1)),
                on_click=lambda _,i=pi: self._activar_plato(i),
                ink=True,
                tooltip="Activar este plato")

            target=ft.DragTarget(
                content=ft.Container(content=plato_box,padding=0,margin=0,alignment=ft.Alignment(-1,-1)),
                group="items",
                data=str(pi),
                on_accept=self._on_drop,
                on_will_accept=self._on_will,
                expand=False,
            )
            self.lv_content.controls.append(target)

        self.txt_total.value=f"${self.state.total()}"
        self.page.update()

    def _on_will(self,e):
        e.control.content.border=ft.Border.all(2,GREEN) if e.accept else ft.Border.all(1,ACCENT2)
        self.page.update()

    def _on_drop(self,e):
        dst=int(e.control.data)
        src_data=e.src.data  # e.src is the Draggable object
        info=self._drag_map.get(src_data)
        if info is None: return
        self.state.mover_item(info["sp"],info["si"],dst)
        self.refresh()

    def _quitar(self,e):
        pi,ii=[int(x) for x in e.control.data.split(":")]
        pl=self.state.platos[pi]
        pl.items[ii]["qty"]-=1
        if pl.items[ii]["qty"]<=0: pl.items.pop(ii)
        self.refresh()

    def _edit_name(self,e):
        self._editing_idx=e.control.data; self.refresh()

    def _rename_done(self,e,idx):
        self.state.platos[idx].nombre=e.control.value; self._editing_idx=-1; self.refresh()

    def _dup(self,e):
        self.state.duplicar(e.control.data); self.refresh()

    def _del(self,e):
        self.state.eliminar(e.control.data); self.refresh()

    def _activar_plato(self,idx):
        if 0<=idx<len(self.state.platos):
            self.state.activo=idx
            self.refresh()

    def build(self):
        # Header del panel
        header=ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text("🧾",size=22),
                    width=42,height=42,
                    bgcolor=SURFACE_HIGH,
                    border_radius=21,
                    alignment=ft.Alignment(0,0),
                    border=ft.Border.all(2,HIGHLIGHT),
                ),
                ft.Column([
                    ft.Text("Resumen del pedido",size=17,weight=ft.FontWeight.W_900,color=GOLD),
                    ft.Text("Arrastra para mover entre platos",size=10,color=TXT_MUTED),
                ],spacing=0),
            ],spacing=10,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding(2,2,2,8),
        )
        # Total con estilo moderno
        total_box=ft.Container(
            content=ft.Row([
                ft.Column([
                    ft.Text("TOTAL A PAGAR",size=10,color="white",weight=ft.FontWeight.W_700),
                    self.txt_total,
                ],spacing=0),
                ft.Container(expand=True),
                ft.Icon(ft.Icons.ATTACH_MONEY,color="white",size=28),
            ],vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ACCENT,
            border_radius=14,
            padding=ft.Padding(16,10,16,10),
            shadow=ft.BoxShadow(spread_radius=0,blur_radius=8,color=SHADOW_BLACK_MED,offset=ft.Offset(0,3)),
        )
        return ft.Container(
            content=ft.Column([
                header,
                ft.Row([self.dd_plato],spacing=0,alignment=ft.MainAxisAlignment.START),
                ft.Container(height=1,bgcolor=DIVIDER_SOFT),
                self.lv,
                ft.Container(height=1,bgcolor=DIVIDER_SOFT),
                total_box,
            ],expand=True,spacing=8),
            expand=5,bgcolor=BG_CARD,border_radius=14,padding=12,
            border=ft.Border.all(1,ACCENT_SOFT),
            shadow=ft.BoxShadow(spread_radius=0,blur_radius=12,color=SHADOW_BLACK_MED,offset=ft.Offset(0,4)))


class HistorialDialog:
    def __init__(self,page,on_edit_pedido,on_ticket_impreso):
        self.page=page
        self.on_edit_pedido=on_edit_pedido
        self.on_ticket_impreso=on_ticket_impreso
        self._dlg=None

    def _mostrar_estado_impresion(self, ok: bool):
        txt = "Impresion Exitosa" if ok else "Error de impresion"
        bg = GREEN if ok else ERROR_RED
        self.page.snack_bar=ft.SnackBar(ft.Text(txt,color="white"),bgcolor=bg)
        self.page.snack_bar.open=True
        self.page.update()

    def _confirmar_edicion(self,pedido):
        warn_header=ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED,color="white",size=28),
                    width=52,height=52,
                    bgcolor=ft.Colors.with_opacity(0.22,"white"),
                    border_radius=26,
                    alignment=ft.Alignment(0,0),
                ),
                ft.Column([
                    ft.Text("Editar pedido",size=17,weight=ft.FontWeight.W_900,color="white"),
                    ft.Text("Confirma para mover a la pantalla principal",size=11,color=ft.Colors.with_opacity(0.85,"white")),
                ],spacing=2,alignment=ft.MainAxisAlignment.CENTER),
            ],spacing=12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=HIGHLIGHT,
            padding=ft.Padding(16,12,16,12),
            border_radius=ft.BorderRadius(top_left=14,top_right=14,bottom_left=0,bottom_right=0),
        )
        dlg=ft.AlertDialog(
            title=warn_header,
            title_padding=ft.Padding.all(0),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Se quitará este pedido de la lista y se cargará en la pantalla principal para editarlo.",
                        color=TXT,size=13,
                    ),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE,color=TXT_MUTED,size=14),
                            ft.Text("Esta acción no puede deshacerse desde la lista.",color=TXT_MUTED,size=11,italic=True),
                        ],spacing=6),
                        bgcolor=BG_PANEL,
                        padding=ft.Padding(10,8,10,8),
                        border_radius=10,
                    ),
                ],spacing=10,tight=True),
                width=380,
            ),
            bgcolor=BG_CARD,
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        def cancelar(_e):
            dlg.open=False
            self.page.update()
        def aceptar(_e):
            dlg.open=False
            eliminado=eliminar_pedido(pedido)
            if self._dlg:
                self._dlg.open=False
            self.page.update()
            if eliminado:
                self.on_edit_pedido(pedido)
        dlg.actions=[
            ft.TextButton("Cancelar",on_click=cancelar,style=ft.ButtonStyle(color=TXT_MUTED)),
            ft.TextButton("Aceptar",on_click=aceptar,style=ft.ButtonStyle(color=ACCENT)),
        ]
        self.page.overlay.append(dlg)
        dlg.open=True
        self.page.update()

    def _pedido_card(self,p):
        # Client info lines
        info=[]
        if p.get("domicilio"): info.append(("📍",p['domicilio']))
        if p.get("cruces"): info.append(("🧭",p['cruces']))
        if p.get("telefono"): info.append(("📞",p['telefono']))
        hora_especifica = p.get("hora_especifica","")

        def reimprimir(_e,ped=p):
            ticket=generar_ticket_impresion(ped)
            print("\n"+ticket)
            ok,msg=printer.imprimir(ticket)
            play_notification_sound("print_success" if ok else "print_error")
            if ok:
                self.on_ticket_impreso()
            self._mostrar_estado_impresion(ok)

        def editar(_e,ped=p):
            self._confirmar_edicion(ped)

        # Top: hora del pedido (compra) + hora específica destacada
        hora_compra=p.get('hora','')
        top_row=ft.Row([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SCHEDULE,color=TXT_MUTED,size=12),
                    ft.Text(hora_compra,color=TXT_MUTED,size=11,weight=ft.FontWeight.W_600),
                ],spacing=4),
                bgcolor=SURFACE_HIGH,
                padding=ft.Padding(8,3,8,3),
                border_radius=10,
                border=ft.Border.all(1,ACCENT_SOFT),
            ),
            ft.Container(expand=True),
            ft.Container(
                content=ft.Row([
                    ft.Text("⏰",size=14),
                    ft.Text(hora_especifica,color="white",size=14,weight=ft.FontWeight.W_900),
                ],spacing=4),
                bgcolor=HIGHLIGHT,
                padding=ft.Padding(10,4,10,4),
                border_radius=12,
            ) if hora_especifica else ft.Container(),
        ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        cliente_section=ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(emo,size=12),
                    ft.Text(val,color=TXT,size=12,weight=ft.FontWeight.W_700),
                ],spacing=6) for emo,val in info
            ],spacing=2),
            padding=ft.Padding(0,2,0,2),
        ) if info else ft.Container()

        platos_section=[]
        for pl in p.get("platos",[]):
            items_widgets=[]
            for it in pl.get("items",[]):
                ico=PRODUCT_ICONS.get(it['name'],"🍽️")
                items_widgets.append(ft.Column([
                    ft.Row([
                        ft.Text(ico,size=12),
                        ft.Text(f"{it['qty']}x {it['name']}",color=GOLD,size=12,weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        ft.Text(f"${it['price']*it['qty']}",color=ACCENT,size=12,weight=ft.FontWeight.W_900),
                    ],spacing=6),
                    ft.Container(
                        content=ft.Text(f"→ {it['variant']}",color=TXT_MUTED,size=10,italic=True),
                        padding=ft.Padding(20,0,0,0),
                    ) if it.get('variant') else ft.Container(height=0),
                ],spacing=1))
            platos_section.append(ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Text(pl['nombre'],color="white",size=10,weight=ft.FontWeight.W_900),
                        bgcolor=ACCENT,
                        border_radius=8,
                        padding=ft.Padding(8,2,8,2),
                    ),
                    *items_widgets,
                ],spacing=4),
                padding=ft.Padding(0,4,0,4),
            ))

        return ft.Container(
            content=ft.Column([
                top_row,
                cliente_section,
                ft.Container(height=1,bgcolor=DIVIDER_SOFT),
                *platos_section,
                ft.Container(height=1,bgcolor=DIVIDER_SOFT),
                ft.Row([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.ATTACH_MONEY,color="white",size=14),
                            ft.Text(f"${p.get('total',0)}",color="white",weight=ft.FontWeight.W_900,size=14),
                        ],spacing=2),
                        bgcolor=GREEN,
                        border_radius=10,
                        padding=ft.Padding(10,3,10,3),
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(icon=ft.Icons.PRINT,icon_color=GREEN,icon_size=18,
                                  on_click=reimprimir,padding=0,tooltip="Reimprimir"),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.EDIT,color="white",size=12),
                            ft.Text("Editar",color="white",size=11,weight=ft.FontWeight.W_800),
                        ],spacing=4),
                        bgcolor=ACCENT,
                        border_radius=10,
                        padding=ft.Padding(10,5,10,5),
                        on_click=editar,ink=True,
                    ),
                ],spacing=6,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],spacing=6),
            bgcolor=SURFACE_HIGH,
            border_radius=12,
            padding=12,
            margin=ft.Margin(bottom=8),
            border=ft.Border.all(1,ACCENT_SOFT),
            shadow=ft.BoxShadow(spread_radius=0,blur_radius=4,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,2)))

    def _build_column(self,titulo,emoji,pedidos,acento):
        if not pedidos:
            lista=ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Text("📭",size=32),
                        width=64,height=64,
                        bgcolor=SURFACE_HIGH,
                        border_radius=32,
                        alignment=ft.Alignment(0,0),
                        border=ft.Border.all(1,ACCENT_SOFT),
                    ),
                    ft.Text("Sin pedidos",color=TXT_MUTED,size=13,weight=ft.FontWeight.W_700,text_align=ft.TextAlign.CENTER),
                    ft.Text("Aún no hay registros aquí.",color=TXT_MUTED,size=11,italic=True,text_align=ft.TextAlign.CENTER),
                ],alignment=ft.MainAxisAlignment.CENTER,horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=8),
                alignment=ft.Alignment(0,0),
                expand=True,
                padding=20,
            )
        else:
            lista=ft.ListView(
                controls=[self._pedido_card(p) for p in pedidos],
                expand=True,
                spacing=0,
            )
        col_header=ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text(emoji,size=18),
                    width=36,height=36,
                    bgcolor=SURFACE_HIGH,
                    border_radius=18,
                    alignment=ft.Alignment(0,0),
                    border=ft.Border.all(1,ACCENT_SOFT),
                ),
                ft.Column([
                    ft.Text(titulo,size=13,weight=ft.FontWeight.W_900,color=GOLD),
                    ft.Text(f"{len(pedidos)} pedido(s)",size=10,color=TXT_MUTED),
                ],spacing=0,alignment=ft.MainAxisAlignment.CENTER),
            ],spacing=8,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=acento,
            padding=ft.Padding(10,8,10,8),
            border_radius=10,
        )
        return ft.Container(
            content=ft.Column([
                col_header,
                ft.Container(content=lista,expand=True),
            ],expand=True,spacing=8),
            expand=True,bgcolor=BG_PANEL,border_radius=12,padding=10,
            border=ft.Border.all(1,ACCENT_SOFT))

    def mostrar(self):
        hoy=datetime.now().strftime("%Y-%m-%d")
        pedidos_hoy=[p for p in cargar_pedidos() if p.get("fecha")==hoy]
        con_hora=[p for p in pedidos_hoy if p.get("hora_especifica")]
        sin_hora=[p for p in pedidos_hoy if not p.get("hora_especifica")]

        list_header=ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Text("📋",size=24),
                    width=52,height=52,
                    bgcolor=ft.Colors.with_opacity(0.22,"white"),
                    border_radius=26,
                    alignment=ft.Alignment(0,0),
                ),
                ft.Column([
                    ft.Text("Pedidos del día",size=18,weight=ft.FontWeight.W_900,color="white"),
                    ft.Text(f"{len(pedidos_hoy)} pedidos · {datetime.now().strftime('%d/%m/%Y')}",size=11,color=ft.Colors.with_opacity(0.85,"white")),
                ],spacing=2,alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ATTACH_MONEY,color="white",size=14),
                        ft.Text(f"${sum(p.get('total',0) for p in pedidos_hoy)}",color="white",size=14,weight=ft.FontWeight.W_900),
                    ],spacing=2),
                    bgcolor=ft.Colors.with_opacity(0.22,"white"),
                    border_radius=12,
                    padding=ft.Padding(12,6,12,6),
                ),
            ],spacing=12,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ACCENT,
            padding=ft.Padding(16,12,16,12),
            border_radius=ft.BorderRadius(top_left=14,top_right=14,bottom_left=0,bottom_right=0),
        )

        content=ft.Row([
            self._build_column("Sin hora","🍽️",sin_hora,ACCENT_SOFT),
            self._build_column("Con hora","⏰",con_hora,"#F4D5A0"),
        ],expand=True,spacing=10,height=480,width=780)

        self._dlg=ft.AlertDialog(
            title=list_header,
            title_padding=ft.Padding.all(0),
            content=content,
            bgcolor=BG_CARD,
            shape=ft.RoundedRectangleBorder(radius=14),
        )
        self.page.overlay.append(self._dlg); self._dlg.open=True; self.page.update()


# ═══════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════
def main(page: ft.Page):
    page.title="Punto de Venta — Tortas Susy"
    page.bgcolor=BG_DARK; page.padding=10
    page.window.width=1280; page.window.height=800
    page.theme_mode=ft.ThemeMode.LIGHT
    init_db()
    cargar_pedidos()

    state=PedidoState()
    form=FormularioCliente(page,state)
    resumen=ResumenPedido(page,state)
    ticket_impreso_overlay=ft.Stack(
        visible=False,
        expand=True,
        controls=[
            ft.Container(expand=True,bgcolor=ft.Colors.with_opacity(0.30,"black")),
            ft.Container(
                expand=True,
                alignment=ft.Alignment(0,0),
                content=ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Icon(ft.Icons.CHECK_CIRCLE,color=GREEN,size=64),
                            width=100,height=100,
                            bgcolor="white",
                            border_radius=50,
                            alignment=ft.Alignment(0,0),
                            shadow=ft.BoxShadow(spread_radius=0,blur_radius=10,color=SHADOW_BLACK_MED,offset=ft.Offset(0,4)),
                        ),
                        ft.Text("¡Ticket Impreso!",color="white",size=32,weight=ft.FontWeight.W_900,text_align=ft.TextAlign.CENTER),
                        ft.Text("El pedido fue enviado a la impresora.",color=ft.Colors.with_opacity(0.9,"white"),size=13,text_align=ft.TextAlign.CENTER),
                    ],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=14,tight=True),
                    bgcolor=GREEN,
                    border_radius=24,
                    padding=ft.Padding(56,32,56,32),
                    border=ft.Border.all(3,ft.Colors.with_opacity(0.4,"white")),
                    shadow=ft.BoxShadow(
                        spread_radius=0,
                        blur_radius=20,
                        color=SHADOW_BLACK_STRONG,
                        offset=ft.Offset(0,6),
                    ),
                ),
            ),
        ],
    )
    page.overlay.append(ticket_impreso_overlay)

    def mostrar_mensaje_estado(texto: str, ok: bool):
        page.snack_bar=ft.SnackBar(ft.Text(texto,color="white"),bgcolor=GREEN if ok else ERROR_RED)
        page.snack_bar.open=True
        page.update()

    async def _flash_ticket_impreso():
        if ticket_impreso_overlay in page.overlay:
            page.overlay.remove(ticket_impreso_overlay)
        page.overlay.append(ticket_impreso_overlay)
        ticket_impreso_overlay.visible=True
        page.update()
        await asyncio.sleep(1.2)
        ticket_impreso_overlay.visible=False
        page.update()

    def mostrar_ticket_impreso():
        page.run_task(_flash_ticket_impreso)

    def cargar_pedido_para_editar(ped):
        state.cargar_desde_pedido(ped)
        form.cargar_desde_pedido(ped)
        tel=form.get_tel()
        state.cli_existe=bool(tel and buscar_cliente(tel))
        resumen.refresh()
        mostrar_mensaje_estado("Pedido cargado para edición",True)

    def on_item_accept(name,price,qty,variant):
        if not state.platos:
            state.crear_plato()
        if state.agregar_a_activo(name,price,qty,variant):
            resumen.refresh()
        else:
            page.snack_bar=ft.SnackBar(ft.Text("Selecciona un plato primero",color="white"),bgcolor=ACCENT)
            page.snack_bar.open=True; page.update()

    item_dlg=ItemDialog(page,on_item_accept)
    historial=HistorialDialog(page,cargar_pedido_para_editar,mostrar_ticket_impreso)

    def on_product(name,price):
        if not state.platos:
            state.crear_plato()
        item_dlg.show(name,price)

    menu=MenuProductos(on_product)

    def on_imprimir(_e):
        tel=form.get_tel()
        if tel and not state.cli_existe:
            guardar_cliente(tel,form.tf_dom.value.strip(),form.tf_cru.value.strip())
            state.cli_existe=True
        now=datetime.now()
        ped={"fecha":now.strftime("%Y-%m-%d"),"hora":now.strftime("%H:%M:%S"),
             "telefono":tel,"domicilio":form.tf_dom.value.strip(),"cruces":form.tf_cru.value.strip(),
             "hora_especifica":form.get_hora_str(),
             "platos":[p.to_dict() for p in state.platos],"total":state.total()}
        # Guardar pedido del día en JSON
        guardar_pedido(ped)
        ticket=generar_ticket_impresion(ped)
        print("\n"+ticket)  # Consola siempre
        # Intentar impresión física
        ok,msg=printer.imprimir(ticket)
        play_notification_sound("print_success" if ok else "print_error")
        if ok:
            mostrar_ticket_impreso()
        mostrar_mensaje_estado("Impresion Exitosa" if ok else "Error de impresion",ok)

    def on_limpiar(_e):
        state.limpiar(); form.limpiar(); resumen.refresh()
        play_notification_sound("clean_success")
        mostrar_mensaje_estado("Limpiesa Exitosa",True)

    def on_crear_plato(_e):
        state.crear_plato(); resumen.refresh()

    def on_lista(_e):
        play_notification_sound("list_click")
        historial.mostrar()

    def action_btn(icon,label,bgcolor,fgcolor,fn,subtitle=None):
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon,color=fgcolor,size=18),
                    width=32,height=32,
                    bgcolor=ft.Colors.with_opacity(0.18,fgcolor),
                    border_radius=16,
                    alignment=ft.Alignment(0,0),
                ),
                ft.Column([
                    ft.Text(label,color=fgcolor,size=14,weight=ft.FontWeight.W_900),
                    ft.Text(subtitle,color=ft.Colors.with_opacity(0.85,fgcolor),size=10) if subtitle else ft.Container(height=0),
                ],spacing=0,alignment=ft.MainAxisAlignment.CENTER),
            ],spacing=10,alignment=ft.MainAxisAlignment.START,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=bgcolor,
            border_radius=12,
            padding=ft.Padding(12,8,12,8),
            on_click=fn,ink=True,
            expand=True,
            shadow=ft.BoxShadow(spread_radius=0,blur_radius=6,color=SHADOW_BLACK_LIGHT,offset=ft.Offset(0,2)),
        )
    btns=ft.Column([
        ft.Row([
            action_btn(ft.Icons.DELETE_OUTLINE,"Limpiar",ACCENT,"white",on_limpiar,"Reiniciar pedido"),
            action_btn(ft.Icons.PRINT,"Imprimir",GREEN,"white",on_imprimir,"Generar ticket"),
        ],spacing=8),
        ft.Row([
            action_btn(ft.Icons.ADD_CIRCLE_OUTLINE,"Plato","#3F6E8C","white",on_crear_plato,"Nuevo plato"),
            action_btn(ft.Icons.RECEIPT_LONG,"Lista",HIGHLIGHT,"white",on_lista,"Pedidos del día"),
        ],spacing=8),
    ],spacing=8)

    lado_izq=ft.Container(content=ft.Column([
        form.build(),ft.Container(content=menu.build(),expand=True),btns
    ],spacing=8,expand=True),expand=5)

    # Marca de agua discreta en la esquina inferior derecha
    watermark=ft.Row([
        ft.Container(expand=True),
        ft.Text("Created by BrianP",size=9,color=TXT_MUTED,italic=True,weight=ft.FontWeight.W_500),
    ],spacing=0)

    page.add(ft.Column([
        ft.Container(
            content=ft.Row([lado_izq,resumen.build()],expand=True,spacing=10),
            expand=True,
        ),
        watermark,
    ],expand=True,spacing=2))

if __name__=="__main__":
    ft.run(main)
