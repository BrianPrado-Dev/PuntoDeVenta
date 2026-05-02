"""
Punto de Venta (POS) — Tortas Susy
Flet 0.84+ | SQLite3 | JSON | OOP
"""
import flet as ft
import sqlite3, json, os, copy
from datetime import datetime

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

MENU = {
    "Comida": [("Torta",60),("Taco Dorado",10),("Taco c/Carne",25),("Kilo de Carne",300)],
    "Paquetes": [("Paquete #1",90),("Paquete #2",95),("Paquete #3",220),("Paquete #4",345),("Paquete #5",680)],
    "Bebidas": [("Refresco",30),("Cerveza",25),("Agua Fresca 500ml",15),("Agua Fresca 1LT",25),("Caguama",70)],
}

MEAT_TYPES = ["Carne","Buche","Lengua","Mixta"]
TACO_TYPES = ["Papa","Frijol","Requesón","Picadillo"]
DRINK_TYPES = ["Coca","Fanta","Manzana","Sprite","Jamaica","Horchata"]
BEER_TYPES = ["Clara","Obscura"]
AGUA_TYPES = ["Jamaica","Horchata"]
GRID_COLORS = {"Comida":"#F5E7D0","Paquetes":"#EEDCC1","Bebidas":"#F9EFE0"}

BG_DARK="#F2E6D3"; BG_CARD="#FFFDF8"; ACCENT="#B33939"
ACCENT2="#D8C1A0"; TXT="#4A2A22"; GREEN="#16A34A"; GOLD="#8F2D2D"
ERROR_RED="#8B1E1E"
BG_PANEL="#FBF4E8"; BG_ITEM="#F3E6D3"; TXT_MUTED="#8A6F5A"; INPUT_BG="#FFFFFF"

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
        "CREATE TABLE IF NOT EXISTS clientes(telefono TEXT PRIMARY KEY,usuario TEXT,domicilio TEXT,cruces TEXT)"
    ); c.commit(); c.close()

def buscar_cliente(tel):
    c=sqlite3.connect(DB_PATH); r=c.execute(
        "SELECT domicilio,cruces FROM clientes WHERE telefono=?",(tel,)
    ).fetchone(); c.close(); return r

def guardar_cliente(tel,dom,cru):
    c=sqlite3.connect(DB_PATH); c.execute(
        "INSERT OR REPLACE INTO clientes(telefono,usuario,domicilio,cruces) VALUES(?,?,?,?)",
        (tel,"",dom,cru)); c.commit(); c.close()

# ─── JSON ───
def cargar_pedidos():
    if not os.path.exists(PEDIDOS_PATH): return []
    with open(PEDIDOS_PATH,"r",encoding="utf-8") as f:
        try: return json.load(f)
        except: return []

def guardar_pedido(p):
    ps=cargar_pedidos(); ps.append(p)
    with open(PEDIDOS_PATH,"w",encoding="utf-8") as f:
        json.dump(ps,f,ensure_ascii=False,indent=2)

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
                              value="12",disabled=False,**dds)
        self.dd_m=ft.Dropdown(width=88,options=[ft.DropdownOption(key=f"{i:02d}",text=f"{i:02d}") for i in range(0,60,10)],
                              value="00",disabled=False,**dds)
        self.dd_p=ft.Dropdown(width=102,options=[ft.DropdownOption(key="AM",text="AM"),ft.DropdownOption(key="PM",text="PM")],
                              value="PM",disabled=False,**dds)
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
            dd.disabled=False
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
        self.dd_h.disabled=False; self.dd_m.disabled=False; self.dd_p.disabled=False
        self.dd_h.border_color=ACCENT2; self.dd_m.border_color=ACCENT2; self.dd_p.border_color=ACCENT2
        self.dd_h.focused_border_color=ACCENT2; self.dd_m.focused_border_color=ACCENT2; self.dd_p.focused_border_color=ACCENT2
        self.dd_h.color=TXT_MUTED; self.dd_m.color=TXT_MUTED; self.dd_p.color=TXT_MUTED
        self.dd_h.value="12"; self.dd_m.value="00"; self.dd_p.value="PM"

    def build(self):
        lbl=lambda t: ft.Text(t,color=GOLD,size=13,weight=ft.FontWeight.BOLD)
        return ft.Container(
            content=ft.Column([
                ft.Text("📝 Datos del cliente",size=14,weight=ft.FontWeight.BOLD,color=GOLD),
                ft.Row([lbl("Domicilio:"),self.tf_dom],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([lbl("Cruces:"),self.tf_cru],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([lbl("Teléfono:"),self.seg_tel,self.tf_tel],spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([lbl("Hora:"),self.seg_hora,
                    ft.Column([self.dd_h,ft.Text("Hora",size=11,color=ACCENT,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=2),
                    ft.Column([self.dd_m,ft.Text("Minutos",size=11,color=ACCENT,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER)],horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=2),
                    self.dd_p],
                       spacing=5,vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ],spacing=8),bgcolor=BG_CARD,border_radius=10,padding=12)


class MenuProductos:
    def __init__(self,on_product_click):
        self.on_click=on_product_click

    def _subtitle(self,categoria,name):
        if categoria=="Comida":
            return {
                "Torta":"Opciones: Carne, Buche, Lengua, Mixta",
                "Taco Dorado":"Opciones: Papa, Frijol, Requesón, Picadillo",
                "Taco c/Carne":"Opciones: Tipo de taco y carne",
                "Kilo de Carne":"Opciones: Tipo de carne y cantidad",
            }.get(name,"")
        if categoria=="Bebidas":
            return {
                "Refresco":"Opciones: Coca, Fanta, Manzana, Sprite, Jamaica, Horchata",
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
        return ft.Container(
            content=ft.Column([
                ft.Text(name,size=name_size,weight=ft.FontWeight.BOLD,color=TXT,text_align=ft.TextAlign.CENTER),
                ft.Text(f"${price}",size=price_size,weight=ft.FontWeight.W_900,color=GOLD,text_align=ft.TextAlign.CENTER),
                ft.Text(
                    subtitle,
                    size=subtitle_size,
                    color=TXT_MUTED,
                    text_align=ft.TextAlign.CENTER,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ) if subtitle else ft.Container(height=0),
            ],alignment=ft.MainAxisAlignment.CENTER,horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=4),
            width=width,height=height,bgcolor=color,border_radius=12,alignment=ft.Alignment(0,0),
            on_click=lambda _,n=name,p=price: self.on_click(n,p),ink=True,
            shadow=ft.BoxShadow(spread_radius=1,blur_radius=6,color=ft.Colors.with_opacity(0.25,"black"),offset=ft.Offset(0,2)))

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
            "Comida":{"runs":2,"w":220,"h":125,"name":18,"price":24,"sub":11,"ratio":1.75},
            "Paquetes":{"runs":3,"w":170,"h":110,"name":16,"price":21,"sub":10,"ratio":1.45},
            "Bebidas":{"runs":2,"w":198,"h":112,"name":18,"price":23,"sub":11,"ratio":1.7},
        }
        return ft.Tabs(
            content=ft.Column([
                ft.TabBar(tabs=[ft.Tab(label=f"{'🍔📦🥤'[i]} {c}") for i,c in enumerate(cats)],
                          indicator_color=ACCENT,label_color=GOLD,unselected_label_color=TXT),
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
            ],expand=True),length=len(cats),selected_index=0,expand=True)

# Colores por bebida
DRINK_COLORS={"Coca":"#8b0000","Fanta":"#cc5500","Manzana":"#8B6914","Sprite":"#2d6e2d","Jamaica":"#722F37","Horchata":"#c8b89a","Clara":"#c8a951","Obscura":"#3b1f0b"}

class ItemDialog:
    """Ventana de selección de variantes para productos."""
    def __init__(self,page,on_accept):
        self.page=page; self.on_accept=on_accept

    def _toggle_btns(self,options,selected,max_sel=None):
        btns=[]
        for opt in options:
            c=ft.Container(
                content=ft.Text(opt,color=TXT,size=16,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER),
                bgcolor=BG_ITEM,border=ft.Border.all(1,ACCENT2),border_radius=10,
                width=145,height=50,alignment=ft.Alignment(0,0),data=opt,ink=True,
                on_click=lambda e,s=selected,mx=max_sel: self._toggle(e,s,mx))
            btns.append(c)
        return btns

    def _toggle(self,e,selected,max_sel):
        opt=e.control.data
        if opt in selected:
            selected.discard(opt)
            e.control.bgcolor=BG_ITEM; e.control.border=ft.Border.all(1,ACCENT2)
        else:
            if max_sel and len(selected)>=max_sel: return
            selected.add(opt)
            e.control.bgcolor=ACCENT; e.control.border=ft.Border.all(2,ACCENT)
        self.page.update()

    def _multiplier(self):
        qty=[1]
        txt=ft.Text("1",size=20,color=TXT,weight=ft.FontWeight.BOLD,width=40,text_align=ft.TextAlign.CENTER)
        def minus(_):
            if qty[0]>1: qty[0]-=1; txt.value=str(qty[0]); self.page.update()
        def plus(_):
            qty[0]+=1; txt.value=str(qty[0]); self.page.update()
        row=ft.Row([
            ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE,icon_color=ACCENT,icon_size=30,on_click=minus),
            ft.Container(content=txt,bgcolor=BG_ITEM,border_radius=8,padding=ft.Padding(12,6,12,6),border=ft.Border.all(1,ACCENT2)),
            ft.IconButton(icon=ft.Icons.ADD_CIRCLE,icon_color=GREEN,icon_size=30,on_click=plus),
        ],alignment=ft.MainAxisAlignment.CENTER)
        return row,qty

    def _section(self,title,controls):
        return ft.Column([ft.Text(title,color=GOLD,size=13,weight=ft.FontWeight.BOLD),
            ft.Row(controls,wrap=True,spacing=10,run_spacing=10,alignment=ft.MainAxisAlignment.CENTER)],spacing=6)

    def _drink_btns(self,options,selected,max_sel=None):
        btns=[]
        for opt in options:
            bg=DRINK_COLORS.get(opt,BG_ITEM)
            c=ft.Container(
                content=ft.Text(opt,color="white",size=14,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER),
                bgcolor=bg,border=ft.Border.all(1,ACCENT2),border_radius=10,
                width=130,height=45,alignment=ft.Alignment(0,0),data=f"{opt}|{bg}",ink=True,
                on_click=lambda e,s=selected,mx=max_sel: self._drink_toggle(e,s,mx))
            btns.append(c)
        return btns

    def _drink_toggle(self,e,selected,max_sel):
        parts=e.control.data.split("|")
        opt=parts[0]; orig_bg=parts[1]
        if opt in selected:
            selected.discard(opt)
            e.control.bgcolor=orig_bg; e.control.border=ft.Border.all(1,ACCENT2)
        else:
            if max_sel and len(selected)>=max_sel:
                # Deselect previous
                for s in list(selected): selected.discard(s)
                for c in e.control.parent.controls:
                    if hasattr(c,'data') and c.data:
                        p=c.data.split("|")
                        if len(p)==2: c.bgcolor=p[1]; c.border=ft.Border.all(1,ACCENT2)
            selected.add(opt)
            e.control.bgcolor="#ffffff30"; e.control.border=ft.Border.all(3,"white")
        self.page.update()

    def _close_dlg(self,dlg):
        dlg.open=False; self.page.update()

    def _warn(self):
        self.page.snack_bar=ft.SnackBar(ft.Text("Seleccionar por lo menos 1 opción",color="white"),bgcolor=ACCENT)
        self.page.snack_bar.open=True; self.page.update()

    def _accept_btn(self,on_click):
        return ft.Row([ft.Button("✅ Aceptar",on_click=on_click,bgcolor=GREEN,color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),height=36,width=160)
        ],alignment=ft.MainAxisAlignment.CENTER)

    def show(self,name,price):
        if name=="Torta": self._show_meat(name,price,2)
        elif name=="Taco Dorado": self._show_taco_dorado(name,price)
        elif name=="Taco c/Carne": self._show_taco_carne(name,price)
        elif name=="Kilo de Carne": self._show_kilo(name,price)
        elif name in ("Paquete #1","Paquete #2"): self._show_paq12(name,price)
        elif name in ("Paquete #3","Paquete #4","Paquete #5"): self._show_simple(name,price)
        elif name=="Refresco": self._show_sel(name,price,"🥤","Tipo de refresco:",DRINK_TYPES)
        elif name=="Cerveza": self._show_sel(name,price,"🍺","Tipo de cerveza:",BEER_TYPES)
        elif name in ("Agua Fresca 500ml","Agua Fresca 1LT"): self._show_sel(name,price,"🥤","Tipo de agua fresca:",AGUA_TYPES)
        elif name=="Caguama": self._show_simple(name,price)

    def _show_meat(self,name,price,max_sel):
        sel=set(); btns=self._toggle_btns(MEAT_TYPES,sel,max_sel=max_sel)
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,title=ft.Text(f"🌮 {name} — ${price}",color=GOLD,weight=ft.FontWeight.BOLD))
        def accept(_):
            if not sel: self._warn(); return
            self.on_accept(name,price,qty[0],", ".join(sorted(sel))); self._close_dlg(dlg)
        dlg.content=ft.Column([self._section("Tipo de carne (máx 2):" if max_sel==2 else "Tipo de carne:",btns),
            ft.Divider(color=ACCENT2),ft.Text("Cantidad:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),mul,
            self._accept_btn(accept)],spacing=12,tight=True,width=350)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_taco_dorado(self,name,price):
        sel=set(); btns=self._toggle_btns(TACO_TYPES,sel)
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,title=ft.Text(f"🌮 {name} — ${price}",color=GOLD,weight=ft.FontWeight.BOLD))
        def accept(_):
            if not sel: self._warn(); return
            self.on_accept(name,price,qty[0],", ".join(sorted(sel))); self._close_dlg(dlg)
        dlg.content=ft.Column([self._section("Tipo de taco:",btns),
            ft.Divider(color=ACCENT2),ft.Text("Cantidad:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),mul,
            self._accept_btn(accept)],spacing=12,tight=True,width=350)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_taco_carne(self,name,price):
        sel_t=set(); btns_t=self._toggle_btns(TACO_TYPES,sel_t)
        sel_m=set(); btns_m=self._toggle_btns(MEAT_TYPES,sel_m)
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,title=ft.Text(f"🌮 {name} — ${price}",color=GOLD,weight=ft.FontWeight.BOLD))
        def accept(_):
            if not sel_t or not sel_m: self._warn(); return
            v=f"Taco: {', '.join(sorted(sel_t))} | Carne: {', '.join(sorted(sel_m))}"
            self.on_accept(name,price,qty[0],v); self._close_dlg(dlg)
        dlg.content=ft.Column([self._section("Tipo de taco:",btns_t),self._section("Tipo de carne:",btns_m),
            ft.Divider(color=ACCENT2),ft.Text("Cantidad:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),mul,
            self._accept_btn(accept)],spacing=12,tight=True,width=380)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_kilo(self,name,price):
        sel=set(); btns=self._toggle_btns(MEAT_TYPES,sel,max_sel=1)
        mul,qty=self._multiplier()
        mode=["gramos"]
        tf_g=ft.TextField(value="",width=120,dense=True,text_size=14,color=TXT,border_color=ACCENT2,suffix=ft.Text("g"),keyboard_type=ft.KeyboardType.NUMBER)
        tf_d=ft.TextField(value="",width=120,dense=True,text_size=14,color=TXT,border_color=ACCENT2,suffix=ft.Text("$"),keyboard_type=ft.KeyboardType.NUMBER,disabled=True)
        seg=ft.SegmentedButton(segments=[ft.Segment(value="gramos",label=ft.Text("Gramos")),ft.Segment(value="dinero",label=ft.Text("Dinero $"))],
            selected=["gramos"],allow_empty_selection=False,on_change=lambda e: _mc(e))
        def _mc(e):
            mode[0]=list(seg.selected)[0]; tf_g.disabled=(mode[0]!="gramos"); tf_d.disabled=(mode[0]!="dinero"); tf_g.value=""; tf_d.value=""; self.page.update()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,title=ft.Text(f"🥩 {name} — ${price}/kg",color=GOLD,weight=ft.FontWeight.BOLD))
        def accept(_):
            if not sel: self._warn(); return
            try:
                if mode[0]=="gramos": g=int(tf_g.value); d=round(g*300/1000)
                else: d=int(tf_d.value); g=round(d*1000/300)
            except: self._warn(); return
            if g<=0 and d<=0: return
            v=f"{', '.join(sel)} - {g}g (${d})"
            self.on_accept(name,d,qty[0],v); self._close_dlg(dlg)
        dlg.content=ft.Column([self._section("Tipo de carne:",btns),ft.Divider(color=ACCENT2),
            ft.Text("Cantidad:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),seg,
            ft.Row([ft.Column([ft.Text("Gramos",color=TXT,size=11),tf_g],spacing=2),ft.Column([ft.Text("Dinero",color=TXT,size=11),tf_d],spacing=2)],spacing=16),
            ft.Divider(color=ACCENT2),ft.Text("Multiplicador:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),mul,
            self._accept_btn(accept)],spacing=10,tight=True,width=400)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_paq12(self,name,price):
        sel_m=set(); btns_m=self._toggle_btns(MEAT_TYPES,sel_m,max_sel=2)
        sel_t=set(); btns_t=self._toggle_btns(TACO_TYPES,sel_t)
        sel_d=set(); btns_d=self._drink_btns(DRINK_TYPES,sel_d,max_sel=1)
        sel_b=set(); btns_beer=self._drink_btns(BEER_TYPES,sel_b,max_sel=1)
        use_beer=[False]
        beer_toggle=ft.SegmentedButton(
            segments=[ft.Segment(value="refresco",label=ft.Text("Refresco")),ft.Segment(value="cerveza",label=ft.Text("🍺 Cerveza +$5"))],
            selected=["refresco"],allow_empty_selection=False,on_change=lambda e: _bt(e))
        drink_row=ft.Row(btns_d,wrap=True,spacing=8,run_spacing=8,alignment=ft.MainAxisAlignment.CENTER)
        beer_row=ft.Row(btns_beer,wrap=True,spacing=8,run_spacing=8,alignment=ft.MainAxisAlignment.CENTER,visible=False)
        def _bt(e):
            v=list(beer_toggle.selected)[0]; use_beer[0]=(v=="cerveza")
            drink_row.visible=not use_beer[0]; beer_row.visible=use_beer[0]
            sel_d.clear(); sel_b.clear()
            for b in btns_d:
                p=b.data.split("|"); b.bgcolor=p[1]; b.border=ft.Border.all(1,ACCENT2)
            for b in btns_beer:
                p=b.data.split("|"); b.bgcolor=p[1]; b.border=ft.Border.all(1,ACCENT2)
            self.page.update()
        mul,qty=self._multiplier()
        col_left=ft.Column([self._section("Carne de torta (máx 2):",btns_m),self._section("Tipo de tacos:",btns_t)],spacing=10,expand=True)
        col_right=ft.Column([ft.Text("Bebida:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),beer_toggle,drink_row,beer_row],spacing=8,expand=True)
        dlg=ft.AlertDialog(bgcolor=BG_CARD,title=ft.Text(f"📦 {name} — ${price}",color=GOLD,weight=ft.FontWeight.BOLD))
        def accept(_):
            if not sel_m or not sel_t: self._warn(); return
            if use_beer[0] and not sel_b: self._warn(); return
            if not use_beer[0] and not sel_d: self._warn(); return
            fp=price+5 if use_beer[0] else price
            beb=f"Cerveza {', '.join(sel_b)}" if use_beer[0] else ", ".join(sorted(sel_d))
            v=f"Torta: {', '.join(sorted(sel_m))} | Tacos: {', '.join(sorted(sel_t))} | Bebida: {beb}"
            self.on_accept(name,fp,qty[0],v); self._close_dlg(dlg)
        dlg.content=ft.Column([
            ft.Row([col_left,ft.VerticalDivider(color=ACCENT2,width=1),col_right],spacing=12,vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Divider(color=ACCENT2),ft.Text("Cantidad:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),mul,
            self._accept_btn(accept)],spacing=10,tight=True,width=750,height=520)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_simple(self,name,price):
        mul,qty=self._multiplier()
        ico="📦" if "Paquete" in name else "🍺"
        dlg=ft.AlertDialog(bgcolor=BG_CARD,title=ft.Text(f"{ico} {name} — ${price}",color=GOLD,weight=ft.FontWeight.BOLD))
        def accept(_):
            self.on_accept(name,price,qty[0],""); self._close_dlg(dlg)
        dlg.content=ft.Column([ft.Text("Cantidad:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),mul,
            self._accept_btn(accept)],spacing=12,tight=True,width=300)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()

    def _show_sel(self,name,price,ico,label,options):
        is_drink=any(o in DRINK_COLORS for o in options)
        sel=set()
        btns=self._drink_btns(options,sel,max_sel=1) if is_drink else self._toggle_btns(options,sel,max_sel=1)
        mul,qty=self._multiplier()
        dlg=ft.AlertDialog(bgcolor=BG_CARD,title=ft.Text(f"{ico} {name} — ${price}",color=GOLD,weight=ft.FontWeight.BOLD))
        def accept(_):
            if not sel: self._warn(); return
            self.on_accept(name,price,qty[0],", ".join(sel)); self._close_dlg(dlg)
        dlg.content=ft.Column([self._section(label,btns),ft.Divider(color=ACCENT2),
            ft.Text("Cantidad:",color=GOLD,size=13,weight=ft.FontWeight.BOLD),mul,
            self._accept_btn(accept)],spacing=12,tight=True,width=380)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()


class ResumenPedido:
    """Panel derecho: selector de plato, resumen con drag & drop, total."""
    def __init__(self,page,state):
        self.page=page; self.state=state
        self._drag_map={}  # drag_key -> (plato_idx, item_idx)
        self.dd_plato=ft.Dropdown(label="Plato actual",dense=True,text_size=13,
                                  on_select=self._on_plato_change,expand=True,
                                  border_color=ACCENT2,color=TXT)
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
        self.txt_total=ft.Text("Total: $0",size=20,weight=ft.FontWeight.BOLD,color=GOLD,text_align=ft.TextAlign.CENTER)
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
            # Build items column
            items_col=ft.Column(spacing=2)
            for ii,item in enumerate(plato.items):
                dk=f"{pi}:{ii}"
                self._drag_map[dk]={"sp":pi,"si":ii}
                sub=item["price"]*item["qty"]
                vr=item.get("variant","")
                name_col=ft.Column([ft.Text(item["name"],color=TXT,size=12,weight=ft.FontWeight.BOLD)],spacing=2)
                if vr: name_col.controls.append(ft.Text(f"→ {vr}",color=GOLD,size=11,weight=ft.FontWeight.W_500))
                item_row=ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DRAG_INDICATOR,color=ACCENT2,size=14),
                        ft.Text(f'{item["qty"]}x',color=ACCENT,weight=ft.FontWeight.BOLD,size=12),
                        ft.Container(content=name_col,expand=True),
                        ft.Text(f'${sub}',color=GOLD,weight=ft.FontWeight.BOLD,size=12),
                        ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,icon_color=ACCENT,icon_size=14,
                                      data=f"{pi}:{ii}",on_click=self._quitar,padding=0),
                    ]),bgcolor=BG_ITEM,border_radius=5,padding=ft.Padding(6,4,6,4))
                draggable=ft.Draggable(content=item_row,group="items",data=dk)
                items_col.controls.append(draggable)

            # Plato header
            if self._editing_idx==pi:
                name_ctl=ft.TextField(value=plato.nombre,dense=True,height=30,text_size=12,
                                      color=TXT,width=120,on_submit=lambda e,idx=pi: self._rename_done(e,idx))
            else:
                name_ctl=ft.Text(plato.nombre,color=GOLD,weight=ft.FontWeight.BOLD,size=13)

            header=ft.Row([
                name_ctl,ft.Row([
                    ft.IconButton(icon=ft.Icons.EDIT,icon_color=GOLD,icon_size=14,data=pi,on_click=self._edit_name,padding=0,tooltip="Renombrar"),
                    ft.IconButton(icon=ft.Icons.COPY,icon_color=GREEN,icon_size=14,data=pi,on_click=self._dup,padding=0,tooltip="Duplicar"),
                    ft.IconButton(icon=ft.Icons.DELETE,icon_color=ACCENT,icon_size=14,data=pi,on_click=self._del,padding=0,tooltip="Eliminar"),
                ],spacing=0)
            ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

            plato_box=ft.Container(
                content=ft.Column([header,items_col],spacing=4),
                bgcolor=BG_PANEL,border_radius=8,padding=8,
                margin=ft.Margin(bottom=6),
                border=ft.Border.all(1,ACCENT2))

            target=ft.DragTarget(
                content=ft.Container(content=plato_box,padding=0,margin=0,alignment=ft.Alignment(-1,-1)),
                group="items",
                data=str(pi),
                on_accept=self._on_drop,
                on_will_accept=self._on_will,
                expand=False,
            )
            self.lv_content.controls.append(target)

        self.txt_total.value=f"Total: ${self.state.total()}"
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

    def build(self):
        return ft.Container(
            content=ft.Column([
                ft.Text("🧾 Resumen del pedido",size=24,weight=ft.FontWeight.W_900,color=GOLD,text_align=ft.TextAlign.CENTER),
                ft.Row([self.dd_plato],spacing=0),
                self.lv,
                ft.Divider(color=ACCENT2,height=1),
                ft.Container(content=self.txt_total,alignment=ft.Alignment(0,0),padding=6),
            ],expand=True,spacing=2),
            expand=5,bgcolor=BG_CARD,border_radius=12,padding=10,
            shadow=ft.BoxShadow(spread_radius=1,blur_radius=10,color=ft.Colors.with_opacity(0.35,"black"),offset=ft.Offset(0,3)))


class HistorialDialog:
    def __init__(self,page):
        self.page=page

    def _mostrar_estado_impresion(self, ok: bool):
        txt = "Impresion Exitosa" if ok else "Error de impresion"
        bg = GREEN if ok else ERROR_RED
        self.page.snack_bar=ft.SnackBar(ft.Text(txt,color="white"),bgcolor=bg)
        self.page.snack_bar.open=True
        self.page.update()

    def _pedido_card(self,p):
        # Client info lines
        info=[]
        if p.get("domicilio"): info.append(f"📍 {p['domicilio']}")
        if p.get("cruces"): info.append(f"🔀 {p['cruces']}")
        if p.get("telefono"): info.append(f"📞 {p['telefono']}")
        hora_especifica = p.get("hora_especifica","")

        def reimprimir(_e,ped=p):
            ticket=generar_ticket_impresion(ped)
            print("\n"+ticket)
            ok,msg=printer.imprimir(ticket)
            play_notification_sound("print_success" if ok else "print_error")
            self._mostrar_estado_impresion(ok)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Container(expand=True),
                    ft.Text(
                        f"⏰ {hora_especifica}",
                        color=GOLD,
                        size=22,
                        weight=ft.FontWeight.W_900,
                        text_align=ft.TextAlign.RIGHT,
                    ) if hora_especifica else ft.Container(),
                ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                # Cliente info (destacado)
                *[ft.Text(line,color=TXT,size=12,weight=ft.FontWeight.BOLD) for line in info],
                ft.Divider(color=ACCENT2,height=1),
                # Items por plato (énfasis)
                *[ft.Container(
                    content=ft.Column([
                        ft.Text(pl['nombre'],color=ACCENT,size=11,weight=ft.FontWeight.BOLD),
                        *[ft.Column([
                            ft.Text(f"  {it['qty']}x {it['name']}  ${it['price']*it['qty']}",color=GOLD,size=12,weight=ft.FontWeight.W_500),
                            ft.Text(f"    → {it['variant']}",color=TXT_MUTED,size=10,italic=True) if it.get('variant') else ft.Container(height=0),
                        ],spacing=1) for it in pl.get("items",[])],
                    ],spacing=1),padding=ft.Padding(0,2,0,2),
                ) for pl in p.get("platos",[])],
                ft.Divider(color=ACCENT2,height=1),
                # Total + hora + reimprimir
                ft.Row([
                    ft.Text(f"Total: ${p.get('total',0)}",color=GREEN,weight=ft.FontWeight.BOLD,size=13),
                    ft.Row([
                        ft.Text(p.get('hora',''),color=TXT_MUTED,size=10),
                        ft.IconButton(icon=ft.Icons.PRINT,icon_color=GREEN,icon_size=14,
                                      on_click=reimprimir,padding=0,tooltip="Reimprimir"),
                    ],spacing=2),
                ],alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ],spacing=3),bgcolor=BG_ITEM,border_radius=8,padding=10,margin=ft.Margin(bottom=5))

    def _build_column(self,titulo,pedidos):
        if not pedidos:
            lista=ft.Text("Sin pedidos.",color=TXT,size=13)
        else:
            lista=ft.ListView(
            controls=[self._pedido_card(p) for p in pedidos],
                expand=True)
        return ft.Container(
            content=ft.Column([
                ft.Text(titulo,size=14,weight=ft.FontWeight.BOLD,color=GOLD,
                        text_align=ft.TextAlign.CENTER),
                ft.Divider(color=ACCENT2,height=1),
                ft.Container(content=lista,expand=True),
            ],expand=True),
            expand=True,bgcolor=BG_PANEL,border_radius=8,padding=8)

    def mostrar(self):
        hoy=datetime.now().strftime("%Y-%m-%d")
        pedidos_hoy=[p for p in cargar_pedidos() if p.get("fecha")==hoy]
        con_hora=[p for p in pedidos_hoy if p.get("hora_especifica")]
        sin_hora=[p for p in pedidos_hoy if not p.get("hora_especifica")]

        content=ft.Row([
            self._build_column("🍽️ Sin hora",sin_hora),
            ft.VerticalDivider(color=ACCENT2,width=1),
            self._build_column("⏰ Con hora",con_hora),
        ],expand=True,spacing=8,height=420,width=700)

        dlg=ft.AlertDialog(title=ft.Text("📋 Pedidos del día",color=GOLD,weight=ft.FontWeight.BOLD),
                           content=content,bgcolor=BG_CARD)
        self.page.overlay.append(dlg); dlg.open=True; self.page.update()


# ═══════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════
def main(page: ft.Page):
    page.title="Punto de Venta — Tortas Susy"
    page.bgcolor=BG_DARK; page.padding=10
    page.window.width=1150; page.window.height=750
    page.theme_mode=ft.ThemeMode.LIGHT
    init_db()

    state=PedidoState()
    form=FormularioCliente(page,state)
    resumen=ResumenPedido(page,state)
    historial=HistorialDialog(page)

    def mostrar_mensaje_estado(texto: str, ok: bool):
        page.snack_bar=ft.SnackBar(ft.Text(texto,color="white"),bgcolor=GREEN if ok else ERROR_RED)
        page.snack_bar.open=True
        page.update()

    def on_item_accept(name,price,qty,variant):
        if not state.platos:
            state.crear_plato()
        if state.agregar_a_activo(name,price,qty,variant):
            resumen.refresh()
        else:
            page.snack_bar=ft.SnackBar(ft.Text("Selecciona un plato primero",color="white"),bgcolor=ACCENT)
            page.snack_bar.open=True; page.update()

    item_dlg=ItemDialog(page,on_item_accept)

    def on_product(name,price):
        if not state.platos:
            state.crear_plato()
        item_dlg.show(name,price)

    menu=MenuProductos(on_product)
    bs=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))

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
        # Siempre guardar primero (JSON + SQLite)
        guardar_pedido(ped)
        ticket=generar_ticket_impresion(ped)
        print("\n"+ticket)  # Consola siempre
        # Intentar impresión física
        ok,msg=printer.imprimir(ticket)
        play_notification_sound("print_success" if ok else "print_error")
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

    btns=ft.Column([
        ft.Row([
            ft.Button("🖨️ Imprimir",on_click=on_imprimir,bgcolor=GREEN,color="white",style=bs,height=36,expand=True),
            ft.Button("🗑️ Limpiar",on_click=on_limpiar,bgcolor=ACCENT,color="white",style=bs,height=36,expand=True),
        ],spacing=6),
        ft.Row([
            ft.Button("➕ Plato",on_click=on_crear_plato,bgcolor=ACCENT2,color=TXT,style=bs,height=36,expand=True),
            ft.Button("📋 Lista",on_click=on_lista,bgcolor=BG_PANEL,color=TXT,style=bs,height=36,expand=True),
        ],spacing=6),
    ],spacing=4)

    lado_izq=ft.Container(content=ft.Column([
        form.build(),ft.Container(content=menu.build(),expand=True),btns
    ],spacing=8,expand=True),expand=5)

    page.add(ft.Row([lado_izq,resumen.build()],expand=True,spacing=10))

if __name__=="__main__":
    ft.run(main)
