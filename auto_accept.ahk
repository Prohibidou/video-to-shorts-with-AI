#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; ============================================================
;  AUTO-ACCEPT BOT v3 - ImageSearch (CONFIABLE)
;  Captura imagen del botón → busca esa imagen exacta en pantalla
; ============================================================

BotActivo := false
BotPausado := false
TotalClicks := 0
CHECK_INTERVAL := 500
CLICK_DELAY := 1500
IMAGE_TOLERANCE := 50  ; 0-255, tolerancia para ImageSearch
LogTextGlobal := ""
ScriptDir := A_ScriptDir

; Región de búsqueda
SearchX1 := 0
SearchY1 := 0
SearchX2 := A_ScreenWidth
SearchY2 := A_ScreenHeight
RegionSet := false

; Imagen de referencia del botón
ButtonImagePath := ScriptDir "\button_template.bmp"
ImageCaptured := FileExist(ButtonImagePath) ? true : false

CrearGUI()

; ============================================================
CrearGUI() {
    global

    MainGui := Gui("+AlwaysOnTop -MaximizeBox", "Auto-Accept Bot v3")
    MainGui.BackColor := "1E1E1E"
    MainGui.OnEvent("Close", (*) => ExitApp())

    ; === HEADER ===
    MainGui.SetFont("s14 Bold c0078D4", "Segoe UI")
    MainGui.Add("Text", "x20 y10 w440 Center", "⚡ AUTO-ACCEPT BOT v3")
    MainGui.SetFont("s8 Norm c888888", "Segoe UI")
    MainGui.Add("Text", "x20 y35 w440 Center", "ImageSearch — Busca la imagen exacta del botón")

    ; === PASO 1: CAPTURAR BOTÓN ===
    MainGui.SetFont("s9 cD4D4D4", "Segoe UI")
    MainGui.Add("GroupBox", "x15 y60 w450 h85 cD4D4D4", "① Capturar el botón (solo 1 vez)")

    MainGui.SetFont("s9 cWhite", "Segoe UI")
    BtnCapture := MainGui.Add("Button", "x30 y82 w200 h30", "📸 Capturar Botón")
    BtnCapture.OnEvent("Click", StartCapture)

    MainGui.SetFont("s9 Bold cDCDCAA", "Consolas")
    CaptureLabel := MainGui.Add("Text", "x240 y82 w210 h30 vCaptureLabel +0x200",
        ImageCaptured ? "✅ Imagen guardada" : "⚠ Sin imagen")

    MainGui.SetFont("s7 c888888", "Segoe UI")
    MainGui.Add("Text", "x30 y118 w420", "Arrastrá un rectángulo EXACTO sobre el botón 'Run' cuando aparezca")

    ; === PASO 2: REGIÓN DE BÚSQUEDA (OPCIONAL) ===
    MainGui.SetFont("s9 cD4D4D4", "Segoe UI")
    MainGui.Add("GroupBox", "x15 y150 w450 h60 cD4D4D4", "② Región de búsqueda (opcional, por defecto toda la pantalla)")

    MainGui.SetFont("s9 cWhite", "Segoe UI")
    BtnRegion := MainGui.Add("Button", "x30 y170 w160 h28", "🔲 Limitar Región")
    BtnRegion.OnEvent("Click", StartRegionSelect)

    MainGui.SetFont("s8 cDCDCAA", "Consolas")
    RegionLabel := MainGui.Add("Text", "x200 y170 w250 h28 vRegionLabel +0x200", "Toda la pantalla")

    ; === PASO 3: CONFIGURACIÓN ===
    MainGui.SetFont("s9 cD4D4D4", "Segoe UI")
    MainGui.Add("GroupBox", "x15 y220 w450 h55 cD4D4D4", "③ Configuración")

    MainGui.Add("Text", "x30 y242 w70", "Intervalo:")
    EditInterval := MainGui.Add("Edit", "x100 y239 w45 vEditInterval", "500")
    MainGui.Add("Text", "x148 y242 w25", "ms")

    MainGui.Add("Text", "x180 y242 w65", "Post-clic:")
    EditDelay := MainGui.Add("Edit", "x245 y239 w45 vEditDelay", "1500")
    MainGui.Add("Text", "x293 y242 w25", "ms")

    MainGui.Add("Text", "x325 y242 w65", "Tolerancia:")
    EditTolerance := MainGui.Add("Edit", "x395 y239 w40 vEditTolerance", "50")

    ; === CONTROLES ===
    MainGui.SetFont("s9 cD4D4D4", "Segoe UI")
    MainGui.Add("GroupBox", "x15 y280 w450 h50 cD4D4D4", "④ Controles")

    MainGui.SetFont("s10 Bold cWhite", "Segoe UI")
    BtnStartCtrl := MainGui.Add("Button", "x30 y296 w130 h28", "▶  INICIAR")
    BtnStartCtrl.OnEvent("Click", BtnStart)
    BtnPauseCtrl := MainGui.Add("Button", "x170 y296 w130 h28 Disabled", "⏸  PAUSAR")
    BtnPauseCtrl.OnEvent("Click", BtnPause)
    BtnStopCtrl := MainGui.Add("Button", "x310 y296 w130 h28 Disabled", "⏹  DETENER")
    BtnStopCtrl.OnEvent("Click", BtnStop)

    ; === STATUS ===
    MainGui.SetFont("s12 Bold cF44747", "Segoe UI")
    StatusText := MainGui.Add("Text", "x15 y335 w450 Center vStatusText h25", "⏹ DETENIDO")

    ; === LOG ===
    MainGui.SetFont("s9 cD4D4D4", "Segoe UI")
    MainGui.Add("GroupBox", "x15 y365 w450 h135 cD4D4D4", "📋 Log")
    MainGui.SetFont("s7 c4EC9B0", "Consolas")
    LogDisplay := MainGui.Add("Edit", "x30 y385 w420 h105 vLogDisplay ReadOnly Multi VScroll", "")

    ; === FOOTER ===
    MainGui.SetFont("s8 c666666", "Segoe UI")
    MainGui.Add("Text", "x15 y508 w80", "Clics:")
    MainGui.SetFont("s10 Bold c0078D4", "Segoe UI")
    ClickCount := MainGui.Add("Text", "x60 y506 w40 vClickCount", "0")
    MainGui.SetFont("s7 c555555", "Segoe UI")
    MainGui.Add("Text", "x300 y508 w170 Right", "F1=Start F2=Pause F3=Stop")

    MainGui.Show("w480 h530")

    if (ImageCaptured)
        AgregarLog("Imagen de botón encontrada: " ButtonImagePath)
}

; ============================================================
; CAPTURAR IMAGEN DEL BOTÓN
; ============================================================
StartCapture(*) {
    global

    AgregarLog("Arrastrá sobre el botón 'Run' exactamente...")
    CaptureLabel.Text := "⏳ Arrastrando..."

    MainGui.Minimize()
    Sleep(400)

    ; Overlay
    OverlayGui := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20")
    OverlayGui.BackColor := "000000"
    WinSetTransparent(1, OverlayGui)
    OverlayGui.Show("x0 y0 w" A_ScreenWidth " h" A_ScreenHeight)

    ; Esperar click
    KeyWait("LButton", "D")
    CoordMode("Mouse", "Screen")
    MouseGetPos(&sx, &sy)

    ; Rectángulo visual
    RectGui := Gui("+AlwaysOnTop -Caption +ToolWindow")
    RectGui.BackColor := "00FF00"
    WinSetTransparent(100, RectGui)

    while GetKeyState("LButton", "P") {
        MouseGetPos(&mx, &my)
        rx := Min(sx, mx)
        ry := Min(sy, my)
        rw := Max(Abs(mx - sx), 1)
        rh := Max(Abs(my - sy), 1)
        if (rw > 3 && rh > 3)
            RectGui.Show("x" rx " y" ry " w" rw " h" rh " NoActivate")
        Sleep(16)
    }

    MouseGetPos(&ex, &ey)
    RectGui.Destroy()
    OverlayGui.Destroy()

    captX := Min(sx, ex)
    captY := Min(sy, ey)
    captW := Max(Abs(ex - sx), 1)
    captH := Max(Abs(ey - sy), 1)

    if (captW < 5 || captH < 5) {
        MainGui.Restore()
        AgregarLog("⚠ Selección muy chica, intentá de nuevo")
        CaptureLabel.Text := "⚠ Muy chica"
        return
    }

    ; Capturar con Python
    pythonCmd := 'python "' ScriptDir '\capture_region.py" ' captX ' ' captY ' ' captW ' ' captH ' "' ButtonImagePath '"'
    AgregarLog("Capturando " captW "x" captH " desde (" captX "," captY ")...")

    result := RunWait(A_ComSpec ' /c ' pythonCmd,, "Hide")

    MainGui.Restore()

    if FileExist(ButtonImagePath) {
        ImageCaptured := true
        CaptureLabel.Text := "✅ " captW "x" captH "px guardada"
        AgregarLog("✅ Imagen guardada: " captW "x" captH "px")
    } else {
        CaptureLabel.Text := "❌ Error al capturar"
        AgregarLog("❌ Error al capturar imagen")
    }
}

; ============================================================
; SELECCIONAR REGIÓN (OPCIONAL)
; ============================================================
StartRegionSelect(*) {
    global

    AgregarLog("Arrastrá rectángulo para limitar la búsqueda...")
    MainGui.Minimize()
    Sleep(400)

    OverlayGui := Gui("+AlwaysOnTop -Caption +ToolWindow +E0x20")
    OverlayGui.BackColor := "000000"
    WinSetTransparent(1, OverlayGui)
    OverlayGui.Show("x0 y0 w" A_ScreenWidth " h" A_ScreenHeight)

    KeyWait("LButton", "D")
    CoordMode("Mouse", "Screen")
    MouseGetPos(&sx, &sy)

    RectGui := Gui("+AlwaysOnTop -Caption +ToolWindow")
    RectGui.BackColor := "0078D4"
    WinSetTransparent(60, RectGui)

    while GetKeyState("LButton", "P") {
        MouseGetPos(&mx, &my)
        rx := Min(sx, mx)
        ry := Min(sy, my)
        rw := Abs(mx - sx)
        rh := Abs(my - sy)
        if (rw > 5 && rh > 5)
            RectGui.Show("x" rx " y" ry " w" rw " h" rh " NoActivate")
        Sleep(16)
    }

    MouseGetPos(&ex, &ey)
    RectGui.Destroy()
    OverlayGui.Destroy()

    SearchX1 := Min(sx, ex)
    SearchY1 := Min(sy, ey)
    SearchX2 := Max(sx, ex)
    SearchY2 := Max(sy, ey)
    RegionSet := true

    MainGui.Restore()
    rw := SearchX2 - SearchX1
    rh := SearchY2 - SearchY1
    RegionLabel.Text := rw "x" rh " @ (" SearchX1 "," SearchY1 ")"
    AgregarLog("Región: " rw "x" rh "px")
}

; ============================================================
; FUNCIÓN PRINCIPAL - ImageSearch
; ============================================================
BuscarYAceptar() {
    global
    if (!BotActivo || BotPausado || !ImageCaptured)
        return

    CoordMode("Pixel", "Screen")
    CoordMode("Mouse", "Screen")
    MouseGetPos(&OrigX, &OrigY)

    x1 := SearchX1
    y1 := SearchY1
    x2 := SearchX2
    y2 := SearchY2

    try {
        ImageSearch(&FoundX, &FoundY, x1, y1, x2, y2, "*" IMAGE_TOLERANCE " " ButtonImagePath)

        ; ¡Encontrado! Hacer clic en el CENTRO de la imagen encontrada
        ; ImageSearch devuelve la esquina superior izquierda
        ; No sabemos el tamaño exacto aquí, así que click en el punto + offset
        clickX := FoundX + 30  ; aproximado al centro del botón
        clickY := FoundY + 10

        Click(clickX, clickY)
        TotalClicks++

        ClickCount.Text := String(TotalClicks)
        StatusText.Text := "🖱️ Clic #" TotalClicks " @ " clickX "x" clickY
        StatusText.SetFont("c4EC9B0")
        AgregarLog("✅ Clic #" TotalClicks " @ (" clickX "," clickY ")")

        Sleep(CLICK_DELAY)
        MouseMove(OrigX, OrigY, 0)
        StatusText.Text := "✅ Buscando..."
    } catch {
        ; No encontrado, seguir buscando (normal)
    }
}

; ============================================================
; HANDLERS
; ============================================================
BtnStart(*) {
    global
    if (!ImageCaptured) {
        AgregarLog("⚠ ¡Primero capturá el botón!")
        StatusText.Text := "⚠ ¡Capturá el botón primero!"
        StatusText.SetFont("cDCDCAA")
        return
    }
    saved := MainGui.Submit(false)
    CHECK_INTERVAL := Integer(saved.EditInterval)
    CLICK_DELAY := Integer(saved.EditDelay)
    IMAGE_TOLERANCE := Integer(saved.EditTolerance)
    BotActivo := true
    BotPausado := false

    StatusText.Text := "✅ Buscando..."
    StatusText.SetFont("c4EC9B0")
    BtnStartCtrl.Enabled := false
    BtnPauseCtrl.Enabled := true
    BtnStopCtrl.Enabled := true

    AgregarLog("Bot INICIADO - Tolerancia " IMAGE_TOLERANCE)
    SetTimer(BuscarYAceptar, CHECK_INTERVAL)
}

BtnPause(*) {
    global
    BotPausado := !BotPausado
    if (BotPausado) {
        SetTimer(BuscarYAceptar, 0)
        StatusText.Text := "⏸ PAUSADO"
        StatusText.SetFont("cDCDCAA")
        BtnPauseCtrl.Text := "▶  REANUDAR"
        AgregarLog("Bot PAUSADO")
    } else {
        SetTimer(BuscarYAceptar, CHECK_INTERVAL)
        StatusText.Text := "✅ Buscando..."
        StatusText.SetFont("c4EC9B0")
        BtnPauseCtrl.Text := "⏸  PAUSAR"
        AgregarLog("Bot REANUDADO")
    }
}

BtnStop(*) {
    global
    BotActivo := false
    BotPausado := false
    SetTimer(BuscarYAceptar, 0)
    StatusText.Text := "⏹ DETENIDO"
    StatusText.SetFont("cF44747")
    BtnStartCtrl.Enabled := true
    BtnPauseCtrl.Enabled := false
    BtnStopCtrl.Enabled := false
    BtnPauseCtrl.Text := "⏸  PAUSAR"
    AgregarLog("Bot DETENIDO - Total: " TotalClicks " clics")
}

; ============================================================
; LOG
; ============================================================
AgregarLog(mensaje) {
    global LogTextGlobal, LogDisplay
    ts := FormatTime(, "HH:mm:ss")
    LogTextGlobal := "[" ts "] " mensaje "`n" LogTextGlobal
    if (StrLen(LogTextGlobal) > 3000)
        LogTextGlobal := SubStr(LogTextGlobal, 1, 3000)
    try LogDisplay.Text := LogTextGlobal
}

; ============================================================
; HOTKEYS
; ============================================================
F1:: BtnStart()
F2:: {
    global BotActivo
    if (BotActivo)
        BtnPause()
}
F3:: BtnStop()
