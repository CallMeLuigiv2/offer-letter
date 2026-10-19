// Offer Letter desktop shell (spike S5): starts the Python server as a child
// process inside a Job Object, shows its web UI, and adds a tray icon, a global
// shortcut hook and a mini "call" window.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream};
use std::os::windows::io::AsRawHandle;
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Mutex, OnceLock};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_global_shortcut::ShortcutState;
use windows_sys::Win32::Foundation::HANDLE;
use windows_sys::Win32::System::JobObjects::{
    AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
    SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
};

const CREATE_NO_WINDOW: u32 = 0x0800_0000;
const DEFAULT_HOME: &str = "C:/Users/Owner/OfferLetter";

static START: OnceLock<Instant> = OnceLock::new();
static HOME: OnceLock<PathBuf> = OnceLock::new();
static SERVER_URL: OnceLock<String> = OnceLock::new();
static CHILD: Mutex<Option<Child>> = Mutex::new(None);

fn since_start() -> u128 {
    START.get().map(|s| s.elapsed().as_millis()).unwrap_or(0)
}

/// Appends a timestamped line to `<home>/.data/<file>`.
fn log_to(file: &str, line: &str) {
    let Some(home) = HOME.get() else { return };
    let dir = home.join(".data");
    let _ = std::fs::create_dir_all(&dir);
    let unix_ms = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis()).unwrap_or(0);
    if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true).open(dir.join(file)) {
        let _ = writeln!(f, "{unix_ms} +{}ms {line}", since_start());
    }
}

/// A Job Object that kills every process in it when its last handle closes, i.e.
/// when this process dies for any reason. The handle is intentionally never closed.
fn kill_on_close_job() -> Option<usize> {
    unsafe {
        let job = CreateJobObjectW(std::ptr::null(), std::ptr::null());
        if job.is_null() {
            return None;
        }
        let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        let ok = SetInformationJobObject(
            job,
            JobObjectExtendedLimitInformation,
            &info as *const _ as *const _,
            std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
        );
        if ok == 0 {
            return None;
        }
        Some(job as usize)
    }
}

struct Options {
    home: PathBuf,
    fake_teammates: bool,
}

fn parse_args() -> Options {
    let mut home = std::env::var_os("OFFERLETTER_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(DEFAULT_HOME));
    let mut fake_teammates = false;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        match a.as_str() {
            "--fake-teammates" => fake_teammates = true,
            "--home" => {
                if let Some(v) = args.next() {
                    home = PathBuf::from(v);
                }
            }
            _ => {}
        }
    }
    Options { home, fake_teammates }
}

fn repo_root() -> PathBuf {
    if let Some(p) = std::env::var_os("OFFERLETTER_REPO") {
        return PathBuf::from(p);
    }
    // desktop/src-tauri -> repo root (compile-time path; fine for a personal machine)
    Path::new(env!("CARGO_MANIFEST_DIR")).join("..").join("..").canonicalize().unwrap_or_default()
}

fn free_port() -> std::io::Result<u16> {
    Ok(TcpListener::bind("127.0.0.1:0")?.local_addr()?.port())
}

/// Minimal HTTP GET returning (status, body); no HTTP client dependency.
fn http_get(port: u16, path: &str) -> Option<(u16, String)> {
    let addr: SocketAddr = ([127, 0, 0, 1], port).into();
    let mut s = TcpStream::connect_timeout(&addr, Duration::from_millis(300)).ok()?;
    s.set_read_timeout(Some(Duration::from_millis(1500))).ok()?;
    write!(s, "GET {path} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n").ok()?;
    let mut raw = String::new();
    s.read_to_string(&mut raw).ok()?;
    let status = raw.split_whitespace().nth(1)?.parse().ok()?;
    let body = raw.split("\r\n\r\n").nth(1).unwrap_or("").to_string();
    Some((status, body))
}

fn start_server(opts: &Options, job: Option<usize>) -> Result<u16, String> {
    let port = free_port().map_err(|e| format!("no free port: {e}"))?;
    let server_dir = repo_root().join("server");
    let mut cmd = Command::new("uv");
    cmd.arg("run").arg("--project").arg(&server_dir).args(["offerletter", "serve", "--port"])
        .arg(port.to_string()).arg("--home").arg(&opts.home);
    if opts.fake_teammates {
        cmd.arg("--fake-teammates");
    }
    cmd.stdin(Stdio::null()).stdout(Stdio::null()).stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW);
    let child = cmd.spawn().map_err(|e| format!("could not run uv: {e}"))?;
    log_to("desktop.log", &format!("spawned uv pid={} port={port}", child.id()));
    if let Some(job) = job {
        let ok = unsafe { AssignProcessToJobObject(job as HANDLE, child.as_raw_handle() as HANDLE) };
        log_to("desktop.log", &format!("job assign ok={}", ok != 0));
    }
    *CHILD.lock().unwrap() = Some(child);
    let deadline = Instant::now() + Duration::from_secs(60);
    while Instant::now() < deadline {
        if let Some((200, _)) = http_get(port, "/api/health") {
            log_to("desktop.log", "health OK");
            return Ok(port);
        }
        if let Some(c) = CHILD.lock().unwrap().as_mut() {
            if let Ok(Some(status)) = c.try_wait() {
                return Err(format!("server exited early: {status}"));
            }
        }
        std::thread::sleep(Duration::from_millis(50));
    }
    Err("server did not answer /api/health within 60 s".into())
}

fn governor_summary(port: u16) -> String {
    let Some((200, body)) = http_get(port, "/api/governor") else {
        return "Offer Letter - server not answering".into();
    };
    let Ok(v) = serde_json::from_str::<serde_json::Value>(&body) else {
        return "Offer Letter - governor unreadable".into();
    };
    let mode = v["mode"].as_str().unwrap_or("?");
    let pct = v["five_hour_util"].as_f64().map(|u| format!("{:.0}%", u * 100.0)).unwrap_or("?".into());
    format!("Offer Letter - governor {mode}, 5h usage {pct}")
}

fn show_main(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.unminimize();
        let _ = w.set_focus();
    }
}

fn open_call_window(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("call") {
        let _ = w.show();
        let _ = w.set_focus();
        return;
    }
    let built = WebviewWindowBuilder::new(app, "call", WebviewUrl::App("call.html".into()))
        .title("Offer Letter - Call")
        .inner_size(320.0, 180.0)
        .decorations(false)
        .always_on_top(true)
        .resizable(false)
        .build();
    if let Err(e) = built {
        log_to("desktop.log", &format!("call window failed: {e}"));
    }
}

fn kill_child() {
    if let Some(mut c) = CHILD.lock().unwrap().take() {
        let _ = c.kill();
        let _ = c.wait();
    }
}

fn main() {
    START.set(Instant::now()).ok();
    let opts = parse_args();
    HOME.set(opts.home.clone()).ok();
    log_to("desktop.log", "process start");
    let job = kill_on_close_job();
    log_to("desktop.log", &format!("job object created={}", job.is_some()));

    let shortcut_plugin = tauri_plugin_global_shortcut::Builder::new()
        .with_shortcuts(["ctrl+alt+space"])
        .expect("valid shortcut")
        .with_handler(|_app, _shortcut, event| {
            let state = match event.state() {
                ShortcutState::Pressed => "Pressed",
                ShortcutState::Released => "Released",
            };
            log_to("ptt.log", state);
        })
        .build();

    let app = tauri::Builder::default()
        .plugin(shortcut_plugin)
        .plugin(tauri_plugin_notification::init())
        .on_page_load(|_w, payload| {
            if payload.event() == tauri::webview::PageLoadEvent::Finished {
                let url = payload.url().to_string();
                let tag = if SERVER_URL.get().is_some_and(|s| url.starts_with(s.as_str())) {
                    "server page"
                } else {
                    "local page"
                };
                log_to("desktop.log", &format!("webview loaded ({tag}) {url}"));
            }
        })
        .setup(move |app| {
            let handle = app.handle().clone();
            // Tray first so it exists even if the server is slow.
            let open = MenuItem::with_id(app, "open", "Open", true, None::<&str>)?;
            let call = MenuItem::with_id(app, "call", "Open call window", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &call, &quit])?;
            let mut tray = TrayIconBuilder::with_id("tray")
                .tooltip("Offer Letter - starting")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "open" => show_main(app),
                    "call" => open_call_window(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main(tray.app_handle());
                    }
                });
            if let Some(icon) = app.default_window_icon() {
                tray = tray.icon(icon.clone());
            }
            tray.build(app)?;

            // Server start + navigation happen off the main thread.
            std::thread::spawn(move || match start_server(&opts, job) {
                Ok(port) => {
                    let url = format!("http://127.0.0.1:{port}");
                    SERVER_URL.set(url.clone()).ok();
                    if let Some(w) = handle.get_webview_window("main") {
                        if let Ok(u) = url.parse() {
                            let _ = w.navigate(u);
                        }
                    }
                    loop {
                        let tip = governor_summary(port);
                        if let Some(t) = handle.tray_by_id("tray") {
                            let _ = t.set_tooltip(Some(tip));
                        }
                        std::thread::sleep(Duration::from_secs(10));
                    }
                }
                Err(e) => {
                    log_to("desktop.log", &format!("server start failed: {e}"));
                    if let Some(t) = handle.tray_by_id("tray") {
                        let _ = t.set_tooltip(Some(format!("Offer Letter - {e}")));
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri app");

    app.run(|_app, event| {
        if let RunEvent::Exit = event {
            log_to("desktop.log", "exit");
            kill_child();
        }
    });
}
