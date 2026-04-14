export const EXTENSION_NAME = "Comfy.CoolEffects.VideoPlayer";

const STATE_KEY = "__cool_video_player_widget_state";
const NODE_STATES = new Map();
let EXECUTED_HANDLER = null;
let EXECUTED_API = null;
const DEFAULT_PREVIEW_WIDTH = 320;
const DEFAULT_PREVIEW_HEIGHT = 180;
const PREVIEW_CHROME_HEIGHT = 72;

function log_debug(message, details) {
    if (details === undefined) {
        console.log(`[${EXTENSION_NAME}] ${message}`);
        return;
    }
    console.log(`[${EXTENSION_NAME}] ${message}`, details);
}

function log_warn(message, details) {
    if (details === undefined) {
        console.warn(`[${EXTENSION_NAME}] ${message}`);
        return;
    }
    console.warn(`[${EXTENSION_NAME}] ${message}`, details);
}

function register_widget_state(node, widget_state) {
    if (!widget_state) {
        return;
    }

    const next_node_id = normalize_node_id(node?.id);
    const previous_node_id = normalize_node_id(widget_state.node_id);
    if (previous_node_id.length > 0 && previous_node_id !== next_node_id) {
        NODE_STATES.delete(previous_node_id);
    }
    widget_state.node_id = next_node_id;
    if (next_node_id.length > 0) {
        NODE_STATES.set(next_node_id, widget_state);
    }
}

function normalize_node_id(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value);
}

function build_view_url(video_entry) {
    const filename = String(video_entry?.filename ?? "").trim();
    if (filename.length === 0) {
        return "";
    }

    const file_type = String(video_entry?.type ?? "input").trim() || "input";
    const subfolder = String(video_entry?.subfolder ?? "").trim();
    const query = [
        `filename=${encodeURIComponent(filename)}`,
        `type=${encodeURIComponent(file_type)}`,
    ];
    if (subfolder.length > 0) {
        query.push(`subfolder=${encodeURIComponent(subfolder)}`);
    }
    return `/view?${query.join("&")}`;
}

function extract_video_entry(output_payload) {
    const candidates = [
        output_payload?.ui?.video,
        output_payload?.ui?.video_entries,
        output_payload?.video_entries,
        output_payload?.videos,
        output_payload?.video,
    ];
    for (const candidate of candidates) {
        const entries = Array.isArray(candidate) ? candidate : [candidate];
        for (const entry of entries) {
            if (typeof entry === "string" && entry.trim().length > 0) {
                log_debug("Resolved video entry from string payload.", { entry });
                return {
                    source_url: entry.trim(),
                    filename: "",
                    format: "",
                };
            }
            if (!entry || typeof entry !== "object") {
                continue;
            }
            const source_url = String(entry.source_url ?? entry.url ?? "").trim();
            if (source_url.length > 0) {
                log_debug("Resolved video entry from explicit source URL.", {
                    source_url,
                    filename: entry.filename,
                    type: entry.type,
                    subfolder: entry.subfolder,
                    format: entry.format,
                });
                return {
                    source_url,
                    filename: String(entry.filename ?? "").trim(),
                    format: String(entry.format ?? "").trim(),
                };
            }
            const fallback_url = build_view_url(entry);
            if (fallback_url.length > 0) {
                log_debug("Resolved video entry from filename metadata.", {
                    fallback_url,
                    filename: entry.filename,
                    type: entry.type,
                    subfolder: entry.subfolder,
                    format: entry.format,
                });
                return {
                    source_url: fallback_url,
                    filename: String(entry.filename ?? "").trim(),
                    format: String(entry.format ?? "").trim(),
                };
            }
        }
    }
    log_warn("No usable video entry found in output payload.", output_payload);
    return null;
}

function set_status(widget_state, text) {
    if (widget_state?.status_element) {
        widget_state.status_element.textContent = text;
    }
}

function get_preview_display_width(widget_state) {
    const node_width = Number(widget_state?.node?.size?.[0]);
    if (Number.isFinite(node_width) && node_width > 48) {
        return Math.max(160, Math.round(node_width - 32));
    }
    return DEFAULT_PREVIEW_WIDTH;
}

function update_preview_layout(widget_state, source_width, source_height) {
    if (!widget_state?.canvas_element) {
        return;
    }

    const safe_width = Math.max(1, Number(source_width) || DEFAULT_PREVIEW_WIDTH);
    const safe_height = Math.max(1, Number(source_height) || DEFAULT_PREVIEW_HEIGHT);
    const display_width = get_preview_display_width(widget_state);
    const display_height = Math.max(90, Math.round((display_width * safe_height) / safe_width));

    widget_state.preview_width = safe_width;
    widget_state.preview_height = safe_height;
    widget_state.display_height = display_height;

    widget_state.canvas_element.style.aspectRatio = `${safe_width} / ${safe_height}`;

    if (widget_state.widget) {
        widget_state.widget.computeSize = () => [display_width, display_height + PREVIEW_CHROME_HEIGHT];
    }

    const node = widget_state.node;
    const desired_node_width = Math.max(Number(node?.size?.[0]) || 0, display_width + 16);
    const desired_node_height = Math.max(Number(node?.size?.[1]) || 0, display_height + 110);

    if (node && typeof node.setSize === "function") {
        node.setSize([desired_node_width, desired_node_height]);
    } else if (node) {
        node.size = [desired_node_width, desired_node_height];
    }

    if (node && typeof node.setDirtyCanvas === "function") {
        node.setDirtyCanvas(true, true);
    }
}

function default_request_animation_frame(callback) {
    if (typeof globalThis.requestAnimationFrame === "function") {
        return globalThis.requestAnimationFrame.call(globalThis, callback);
    }
    return globalThis.setTimeout(() => callback(), 16);
}

function default_cancel_animation_frame(handle) {
    if (typeof globalThis.cancelAnimationFrame === "function") {
        globalThis.cancelAnimationFrame.call(globalThis, handle);
        return;
    }
    globalThis.clearTimeout(handle);
}

function default_fetch_ref(resource, options) {
    if (typeof globalThis.fetch !== "function") {
        throw new Error("Fetch API is unavailable.");
    }
    return globalThis.fetch.call(globalThis, resource, options);
}

function default_media_recorder_ref(...args) {
    if (typeof globalThis.MediaRecorder !== "function") {
        throw new Error("MediaRecorder API is unavailable.");
    }
    return new globalThis.MediaRecorder(...args);
}

default_media_recorder_ref.isTypeSupported = (mime_type) =>
    typeof globalThis.MediaRecorder?.isTypeSupported === "function"
        ? globalThis.MediaRecorder.isTypeSupported(mime_type)
        : mime_type === "video/webm";

function create_object_url(url_ref, blob) {
    if (!url_ref || typeof url_ref.createObjectURL !== "function") {
        throw new Error("Object URL API is unavailable.");
    }
    return url_ref.createObjectURL.call(url_ref, blob);
}

function revoke_object_url(url_ref, object_url) {
    if (!url_ref || typeof url_ref.revokeObjectURL !== "function") {
        return;
    }
    url_ref.revokeObjectURL.call(url_ref, object_url);
}

function sanitize_download_name(value) {
    return String(value ?? "")
        .trim()
        .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
        .replace(/\s+/g, " ");
}

function extension_from_mime(mime_type) {
    const normalized = String(mime_type ?? "")
        .toLowerCase()
        .split(";")[0]
        .trim();
    const extension_map = {
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/ogg": "ogv",
        "video/quicktime": "mov",
        "video/x-matroska": "mkv",
    };
    return extension_map[normalized] ?? "";
}

function parse_extension_from_value(value) {
    const clean_value = String(value ?? "").trim();
    if (clean_value.length === 0) {
        return "";
    }

    const without_query = clean_value.split("#")[0].split("?")[0];
    const segment = without_query.split("/").pop() ?? "";
    const dot_index = segment.lastIndexOf(".");
    if (dot_index <= 0 || dot_index === segment.length - 1) {
        return "";
    }
    return segment.slice(dot_index + 1).toLowerCase();
}

function build_download_filename(video_entry, fallback_extension) {
    const explicit_name = sanitize_download_name(video_entry?.filename);
    const entry_extension = parse_extension_from_value(explicit_name);
    const source_extension = parse_extension_from_value(video_entry?.source_url);
    const format_extension = extension_from_mime(video_entry?.format);
    const fallback = parse_extension_from_value(fallback_extension);
    const selected_extension = entry_extension || source_extension || format_extension || fallback || "mp4";

    if (explicit_name.length > 0) {
        if (entry_extension.length > 0) {
            return explicit_name;
        }
        return `${explicit_name}.${selected_extension}`;
    }
    return `cool-effects-preview.${selected_extension}`;
}

function wait_for_media_event(element, event_name, error_names = ["error"]) {
    return new Promise((resolve, reject) => {
        if (!element || typeof element.addEventListener !== "function") {
            reject(new Error(`Missing event target for ${event_name}`));
            return;
        }

        const cleanup = [];
        const add = (name, handler) => {
            element.addEventListener(name, handler, { once: true });
            cleanup.push([name, handler]);
        };
        const clear = () => {
            if (typeof element.removeEventListener !== "function") {
                return;
            }
            for (const [name, handler] of cleanup) {
                element.removeEventListener(name, handler);
            }
        };

        add(event_name, (event) => {
            clear();
            resolve(event);
        });

        for (const error_name of error_names) {
            add(error_name, () => {
                clear();
                reject(new Error(`Media event failed: ${error_name}`));
            });
        }
    });
}

function resolve_media_recorder_mime_type(media_recorder_ref) {
    const candidates = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"];
    const is_supported = media_recorder_ref?.isTypeSupported;
    if (typeof is_supported !== "function") {
        return "video/webm";
    }
    for (const candidate of candidates) {
        if (is_supported(candidate)) {
            return candidate;
        }
    }
    return "";
}

async function export_canvas_video(widget_state) {
    const canvas_element = widget_state?.canvas_element;
    const video_element = widget_state?.video_element;
    if (!canvas_element || typeof canvas_element.captureStream !== "function") {
        throw new Error("Canvas capture is unavailable in this browser.");
    }
    if (!video_element || String(video_element.src ?? "").trim().length === 0) {
        throw new Error("Run the graph to load a video before downloading.");
    }

    const was_playing = Boolean(widget_state.is_playing);
    const previous_time = Number(video_element.currentTime) || 0;
    const previous_loop = Boolean(video_element.loop);
    set_playback_state(widget_state, false);

    if (Number(video_element.readyState) < 1) {
        await wait_for_media_event(video_element, "loadedmetadata");
    }

    update_preview_layout(
        widget_state,
        Number(video_element.videoWidth) || widget_state.preview_width,
        Number(video_element.videoHeight) || widget_state.preview_height,
    );

    const stream = canvas_element.captureStream(30);
    const mime_type = resolve_media_recorder_mime_type(widget_state.media_recorder_ref);
    const recorder = mime_type.length > 0
        ? widget_state.media_recorder_ref(stream, { mimeType: mime_type })
        : widget_state.media_recorder_ref(stream);
    const chunks = [];
    recorder.addEventListener("dataavailable", (event) => {
        if (event?.data && Number(event.data.size) > 0) {
            chunks.push(event.data);
        }
    });

    const stopped_blob = new Promise((resolve, reject) => {
        recorder.addEventListener("stop", () => {
            resolve(new Blob(chunks, { type: mime_type || "video/webm" }));
        }, { once: true });
        recorder.addEventListener("error", () => {
            reject(new Error("Canvas video export failed."));
        }, { once: true });
    });

    const render_export_frame = () => {
        if (recorder.state !== "recording") {
            return;
        }
        if (
            widget_state.context &&
            Number(video_element.readyState) >= 2 &&
            Number(video_element.videoWidth) > 0 &&
            Number(video_element.videoHeight) > 0
        ) {
            if (
                canvas_element.width !== video_element.videoWidth ||
                canvas_element.height !== video_element.videoHeight
            ) {
                canvas_element.width = video_element.videoWidth;
                canvas_element.height = video_element.videoHeight;
            }
            widget_state.context.drawImage(video_element, 0, 0, canvas_element.width, canvas_element.height);
        }
        if (!video_element.ended) {
            widget_state.request_animation_frame(render_export_frame);
        }
    };

    try {
        video_element.loop = false;
        if (typeof video_element.pause === "function") {
            video_element.pause();
        }
        if (typeof video_element.currentTime === "number") {
            video_element.currentTime = 0;
        }

        recorder.start();
        widget_state.request_animation_frame(render_export_frame);
        const ended_promise = video_element.ended
            ? Promise.resolve()
            : wait_for_media_event(video_element, "ended");
        const play_result = typeof video_element.play === "function" ? video_element.play() : null;
        if (play_result && typeof play_result.then === "function") {
            await play_result;
        }
        await ended_promise;
        recorder.stop();
        return await stopped_blob;
    } finally {
        if (typeof stream.getTracks === "function") {
            for (const track of stream.getTracks()) {
                track.stop?.();
            }
        }
        video_element.loop = previous_loop;
        if (typeof video_element.currentTime === "number") {
            video_element.currentTime = previous_time;
        }
        if (was_playing) {
            set_playback_state(widget_state, true);
        }
    }
}

function set_download_button_state(widget_state, disabled) {
    if (!widget_state?.download_button_element) {
        return;
    }
    widget_state.download_button_element.disabled = Boolean(disabled);
    widget_state.download_button_element.style.opacity = disabled ? "0.6" : "1";
    widget_state.download_button_element.style.cursor = disabled ? "not-allowed" : "pointer";
}

function update_toggle_button(widget_state) {
    if (!widget_state?.toggle_button_element) {
        return;
    }
    const is_playing = Boolean(widget_state.is_playing);
    widget_state.toggle_button_element.textContent = is_playing ? "Pause" : "Preview";
    widget_state.toggle_button_element.setAttribute(
        "aria-label",
        is_playing ? "Pause video preview" : "Preview video",
    );
    widget_state.toggle_button_element.setAttribute("aria-pressed", is_playing ? "true" : "false");
}

function update_mute_button(widget_state) {
    if (!widget_state?.mute_button_element) {
        return;
    }
    const is_muted = Boolean(widget_state.is_muted);
    widget_state.mute_button_element.textContent = is_muted ? "\uD83D\uDD07" : "\uD83D\uDD0A";
    widget_state.mute_button_element.setAttribute(
        "aria-label",
        is_muted ? "Unmute audio" : "Mute audio",
    );
    widget_state.mute_button_element.setAttribute("aria-pressed", is_muted ? "true" : "false");
    if (widget_state.video_element) {
        widget_state.video_element.muted = is_muted;
    }
}

function set_playback_state(widget_state, should_play) {
    if (!widget_state || widget_state.stopped) {
        return;
    }

    widget_state.is_playing = Boolean(should_play);
    update_toggle_button(widget_state);

    if (!widget_state.is_playing) {
        if (
            widget_state.animation_handle !== null &&
            typeof widget_state.cancel_animation_frame === "function"
        ) {
            widget_state.cancel_animation_frame(widget_state.animation_handle);
        }
        widget_state.animation_handle = null;
        if (typeof widget_state.video_element?.pause === "function") {
            widget_state.video_element.pause();
        }
        return;
    }

    if (
        widget_state.video_element &&
        String(widget_state.video_element.src ?? "").trim().length > 0 &&
        typeof widget_state.video_element.play === "function"
    ) {
        const play_result = widget_state.video_element.play();
        if (play_result && typeof play_result.then === "function") {
            play_result.catch((error) => {
                const error_message =
                    error && error.message ? error.message : "Unable to start playback.";
                set_status(widget_state, `Preview unavailable: ${error_message}`);
            });
        }
    }

    start_video_preview_loop(widget_state);
}

function stop_video_preview(widget_state) {
    if (!widget_state || widget_state.stopped) {
        return;
    }
    widget_state.stopped = true;
    widget_state.is_playing = false;

    if (
        widget_state.animation_handle !== null &&
        typeof widget_state.cancel_animation_frame === "function"
    ) {
        widget_state.cancel_animation_frame(widget_state.animation_handle);
    }
    widget_state.animation_handle = null;

    if (widget_state.video_element) {
        if (typeof widget_state.video_element.pause === "function") {
            widget_state.video_element.pause();
        }
        widget_state.video_element.src = "";
        if (typeof widget_state.video_element.load === "function") {
            widget_state.video_element.load();
        }
    }
}

function start_video_preview_loop(widget_state) {
    if (!widget_state || widget_state.stopped || !widget_state.is_playing) {
        return;
    }
    if (widget_state.animation_handle !== null) {
        return;
    }

    const render = () => {
        if (widget_state.stopped || !widget_state.is_playing) {
            widget_state.animation_handle = null;
            return;
        }

        const video_element = widget_state.video_element;
        const canvas_element = widget_state.canvas_element;
        const context = widget_state.context;

        if (
            context &&
            video_element &&
            Number(video_element.readyState) >= 2 &&
            Number(video_element.videoWidth) > 0 &&
            Number(video_element.videoHeight) > 0
        ) {
            update_preview_layout(widget_state, video_element.videoWidth, video_element.videoHeight);
            if (
                canvas_element.width !== video_element.videoWidth ||
                canvas_element.height !== video_element.videoHeight
            ) {
                canvas_element.width = video_element.videoWidth;
                canvas_element.height = video_element.videoHeight;
            }
            context.drawImage(video_element, 0, 0, canvas_element.width, canvas_element.height);
        }

        widget_state.animation_handle = widget_state.request_animation_frame(render);
    };

    widget_state.animation_handle = widget_state.request_animation_frame(render);
}

function apply_video_entry(widget_state, video_entry) {
    if (!video_entry || !video_entry.source_url) {
        log_warn("apply_video_entry received no usable video entry.", video_entry);
        widget_state.current_video_entry = null;
        set_download_button_state(widget_state, true);
        set_status(widget_state, "No video preview data available.");
        return false;
    }

    const source_url = String(video_entry.source_url).trim();
    if (source_url.length === 0) {
        log_warn("apply_video_entry received an empty source URL.", video_entry);
        widget_state.current_video_entry = null;
        set_download_button_state(widget_state, true);
        set_status(widget_state, "No video preview data available.");
        return false;
    }

    log_debug("Applying video entry to widget.", video_entry);

    widget_state.current_video_entry = video_entry;
    set_download_button_state(widget_state, false);

    if (widget_state.video_element.src !== source_url) {
        widget_state.video_element.src = source_url;
        if (typeof widget_state.video_element.load === "function") {
            widget_state.video_element.load();
        }
    }

    set_status(widget_state, "Rendering video preview...");
    set_playback_state(widget_state, true);

    return true;
}

async function handle_download_click(widget_state) {
    if (!widget_state || widget_state.stopped) {
        return;
    }
    if (widget_state.is_downloading) {
        return;
    }

    const video_entry = widget_state.current_video_entry;
    const source_url = String(video_entry?.source_url ?? "").trim();
    if (source_url.length === 0) {
        set_status(widget_state, "Run the graph to load a video before downloading.");
        return;
    }
    if (!widget_state.url_ref || typeof widget_state.url_ref.createObjectURL !== "function") {
        set_status(widget_state, "Download is unavailable in this browser.");
        return;
    }
    if (typeof widget_state.media_recorder_ref !== "function") {
        set_status(widget_state, "Canvas download is unavailable in this browser.");
        return;
    }

    widget_state.is_downloading = true;
    set_download_button_state(widget_state, true);
    const previous_status = widget_state.status_element?.textContent ?? "";
    set_status(widget_state, "Rendering canvas download...");

    let object_url = null;
    try {
        const blob = await export_canvas_video(widget_state);
        const filename = build_download_filename(video_entry, extension_from_mime(blob.type));
        object_url = create_object_url(widget_state.url_ref, blob);

        const anchor = widget_state.document_ref.createElement("a");
        anchor.href = object_url;
        anchor.download = filename;
        anchor.rel = "noopener";
        if (typeof anchor.click === "function") {
            anchor.click();
        } else {
            throw new Error("Browser did not expose an anchor click handler.");
        }

        set_status(widget_state, `Downloaded ${filename}`);
    } catch (error) {
        const error_message = error && error.message ? error.message : "Unable to download video.";
        set_status(widget_state, `Download failed: ${error_message}`);
    } finally {
        if (object_url) {
            revoke_object_url(widget_state.url_ref, object_url);
        }
        widget_state.is_downloading = false;
        set_download_button_state(widget_state, !widget_state.current_video_entry);
        if (
            widget_state.current_video_entry &&
            previous_status &&
            String(widget_state.status_element?.textContent ?? "").startsWith("Rendering canvas download")
        ) {
            set_status(widget_state, previous_status);
        }
    }
}

function ensure_executed_listener(api_ref) {
    if (!api_ref || typeof api_ref.addEventListener !== "function") {
        return;
    }
    if (EXECUTED_HANDLER && EXECUTED_API === api_ref) {
        return;
    }

    EXECUTED_HANDLER = (event) => {
        const detail = event?.detail ?? {};
        log_debug("Received executed event.", detail);
        const node_id = normalize_node_id(detail.node);
        if (node_id.length === 0) {
            log_warn("Executed event did not include a node identifier.", detail);
            return;
        }
        const widget_state = NODE_STATES.get(node_id);
        if (!widget_state) {
            log_debug("Executed event ignored because no widget state was registered for node.", {
                node_id,
            });
            return;
        }

        const video_entry = extract_video_entry(detail.output ?? {});
        apply_video_entry(widget_state, video_entry);
    };
    EXECUTED_API = api_ref;
    api_ref.addEventListener("executed", EXECUTED_HANDLER);
}

function maybe_remove_executed_listener() {
    if (NODE_STATES.size !== 0) {
        return;
    }
    if (
        EXECUTED_API &&
        EXECUTED_HANDLER &&
        typeof EXECUTED_API.removeEventListener === "function"
    ) {
        EXECUTED_API.removeEventListener("executed", EXECUTED_HANDLER);
    }
    EXECUTED_HANDLER = null;
    EXECUTED_API = null;
}

export function mount_video_player_widget_for_node({
    node,
    document_ref = globalThis.document,
    request_animation_frame = default_request_animation_frame,
    cancel_animation_frame = default_cancel_animation_frame,
    api_ref = globalThis.app?.api ?? null,
    fetch_ref = default_fetch_ref,
    media_recorder_ref = default_media_recorder_ref,
    url_ref = globalThis.URL,
} = {}) {
    if (!node || typeof node.addDOMWidget !== "function") {
        return null;
    }
    if (!document_ref || typeof document_ref.createElement !== "function") {
        throw new Error("Missing document reference for video player widget");
    }

    const previous_state = node[STATE_KEY];
    if (previous_state) {
        stop_video_preview(previous_state);
        NODE_STATES.delete(normalize_node_id(node.id));
    }

    log_debug("Mounting video player widget.", { node_id: normalize_node_id(node.id) });

    const resolved_request_animation_frame =
        typeof request_animation_frame === "function"
            ? request_animation_frame
            : default_request_animation_frame;
    const resolved_cancel_animation_frame =
        typeof cancel_animation_frame === "function"
            ? cancel_animation_frame
            : default_cancel_animation_frame;

    const container_element = document_ref.createElement("div");
    container_element.setAttribute("data-widget", "cool-video-player");
    Object.assign(container_element.style, {
        display: "grid",
        gap: "6px",
        padding: "8px",
        boxSizing: "border-box",
        width: "100%",
        minWidth: "0",
    });

    const canvas_element = document_ref.createElement("canvas");
    canvas_element.width = 320;
    canvas_element.height = 180;
    canvas_element.setAttribute("aria-label", "Video preview");
    Object.assign(canvas_element.style, {
        width: "100%",
        height: "auto",
        borderRadius: "10px",
        background: "rgb(20, 24, 32)",
        aspectRatio: `${DEFAULT_PREVIEW_WIDTH} / ${DEFAULT_PREVIEW_HEIGHT}`,
        display: "block",
        outline: "1px solid rgb(45, 53, 71)",
    });
    container_element.appendChild(canvas_element);

    const controls_element = document_ref.createElement("div");
    Object.assign(controls_element.style, {
        display: "flex",
        justifyContent: "flex-start",
        gap: "8px",
        flexWrap: "wrap",
    });
    container_element.appendChild(controls_element);

    const toggle_button_element = document_ref.createElement("button");
    toggle_button_element.type = "button";
    Object.assign(toggle_button_element.style, {
        border: "1px solid rgb(72, 87, 117)",
        borderRadius: "999px",
        background: "rgb(34, 42, 58)",
        color: "rgb(232, 238, 247)",
        fontSize: "12px",
        lineHeight: "1.1",
        fontWeight: "600",
        padding: "6px 12px",
        cursor: "pointer",
    });
    controls_element.appendChild(toggle_button_element);

    const download_button_element = document_ref.createElement("button");
    download_button_element.type = "button";
    download_button_element.textContent = "Download";
    download_button_element.setAttribute("aria-label", "Download generated video");
    Object.assign(download_button_element.style, {
        border: "1px solid rgb(72, 87, 117)",
        borderRadius: "999px",
        background: "rgb(28, 54, 90)",
        color: "rgb(232, 238, 247)",
        fontSize: "12px",
        lineHeight: "1.1",
        fontWeight: "600",
        padding: "6px 12px",
        cursor: "pointer",
    });
    controls_element.appendChild(download_button_element);

    const mute_button_element = document_ref.createElement("button");
    mute_button_element.type = "button";
    Object.assign(mute_button_element.style, {
        border: "1px solid rgb(72, 87, 117)",
        borderRadius: "999px",
        background: "rgb(34, 42, 58)",
        color: "rgb(232, 238, 247)",
        fontSize: "14px",
        lineHeight: "1.1",
        fontWeight: "600",
        padding: "6px 10px",
        cursor: "pointer",
    });
    controls_element.appendChild(mute_button_element);

    const status_element = document_ref.createElement("div");
    status_element.setAttribute("aria-live", "polite");
    status_element.setAttribute("role", "status");
    Object.assign(status_element.style, {
        minHeight: "1.2em",
        fontSize: "12px",
        lineHeight: "1.2",
        color: "rgb(143, 154, 179)",
        overflowWrap: "anywhere",
    });
    status_element.textContent = "Connect a VIDEO input and run the graph.";
    container_element.appendChild(status_element);

    const widget = node.addDOMWidget("video_preview", "div", container_element, {
        serialize: false,
        hideOnZoom: false,
    });

    const video_element = document_ref.createElement("video");
    video_element.muted = true;
    video_element.loop = true;
    video_element.volume = 1.0;
    video_element.autoplay = true;
    video_element.playsInline = true;
    video_element.crossOrigin = "anonymous";

    const context =
        typeof canvas_element.getContext === "function"
            ? canvas_element.getContext("2d")
            : null;

    const widget_state = {
        node_id: normalize_node_id(node.id),
        node,
        widget,
        container_element,
        canvas_element,
        context,
        status_element,
        video_element,
        toggle_button_element,
        download_button_element,
        mute_button_element,
        animation_handle: null,
        is_playing: false,
        is_muted: true,
        is_downloading: false,
        stopped: false,
        current_video_entry: null,
        request_animation_frame: resolved_request_animation_frame,
        cancel_animation_frame: resolved_cancel_animation_frame,
        fetch_ref,
        media_recorder_ref,
        url_ref,
        document_ref,
    };
    update_preview_layout(widget_state, DEFAULT_PREVIEW_WIDTH, DEFAULT_PREVIEW_HEIGHT);
    update_toggle_button(widget_state);
    update_mute_button(widget_state);
    set_download_button_state(widget_state, true);
    video_element.addEventListener("loadedmetadata", () => {
        update_preview_layout(widget_state, video_element.videoWidth, video_element.videoHeight);
    });
    video_element.addEventListener("loadeddata", () => {
        update_preview_layout(widget_state, video_element.videoWidth, video_element.videoHeight);
    });
    toggle_button_element.addEventListener("click", () => {
        const next_playing = !widget_state.is_playing;
        set_playback_state(widget_state, next_playing);
        if (!next_playing) {
            set_status(widget_state, "Paused on current frame.");
        } else if (String(widget_state.video_element.src ?? "").trim().length === 0) {
            set_status(widget_state, "Run the graph to load a video preview.");
        } else {
            set_status(widget_state, "");
        }
    });
    download_button_element.addEventListener("click", () => {
        void handle_download_click(widget_state);
    });
    mute_button_element.addEventListener("click", () => {
        widget_state.is_muted = !widget_state.is_muted;
        update_mute_button(widget_state);
    });
    node[STATE_KEY] = widget_state;
    register_widget_state(node, widget_state);

    ensure_executed_listener(api_ref);
    return widget_state;
}

export function unmount_video_player_widget_for_node(node) {
    const widget_state = node?.[STATE_KEY];
    log_debug("Unmounting video player widget.", {
        node_id: normalize_node_id(node?.id),
    });
    stop_video_preview(widget_state);
    if (node) {
        NODE_STATES.delete(normalize_node_id(node.id));
    }
    maybe_remove_executed_listener();
}

export function register_comfy_extension(
    app_ref,
    {
        document_ref = globalThis.document,
        request_animation_frame = default_request_animation_frame,
        cancel_animation_frame = default_cancel_animation_frame,
        api_ref = app_ref?.api ?? null,
        fetch_ref = default_fetch_ref,
        media_recorder_ref = default_media_recorder_ref,
        url_ref = globalThis.URL,
    } = {},
) {
    if (!app_ref || typeof app_ref.registerExtension !== "function") {
        return false;
    }

    app_ref.registerExtension({
        name: EXTENSION_NAME,
        async beforeRegisterNodeDef(nodeType, nodeData) {
            if (nodeData?.name !== "CoolVideoPlayer") {
                return;
            }

            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_executed = nodeType.prototype.onExecuted;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                mount_video_player_widget_for_node({
                    node: this,
                    document_ref,
                    request_animation_frame,
                    cancel_animation_frame,
                    api_ref,
                    fetch_ref,
                    media_recorder_ref,
                    url_ref,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                unmount_video_player_widget_for_node(this);
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
            };

            nodeType.prototype.onExecuted = function onExecuted(output) {
                if (typeof previous_on_executed === "function") {
                    previous_on_executed.apply(this, arguments);
                }

                 log_debug("Node onExecuted received output.", {
                    node_id: normalize_node_id(this?.id),
                    output,
                });

                const widget_state = this?.[STATE_KEY];
                if (!widget_state) {
                    log_warn("Node onExecuted ran without widget state.", {
                        node_id: normalize_node_id(this?.id),
                    });
                    return;
                }

                register_widget_state(this, widget_state);

                const video_entry = extract_video_entry(output ?? {});
                apply_video_entry(widget_state, video_entry);
            };
        },
    });

    return true;
}

export async function auto_register_comfy_extension() {
    let app_ref = globalThis.app;
    if (!app_ref) {
        try {
            const app_module = await import("../../scripts/app.js");
            app_ref = app_module.app;
        } catch (_error) {
            app_ref = null;
        }
    }
    if (app_ref) {
        register_comfy_extension(app_ref);
    }
}

void auto_register_comfy_extension();
