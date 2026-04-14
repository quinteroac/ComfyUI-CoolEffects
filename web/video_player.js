export const EXTENSION_NAME = "Comfy.CoolEffects.VideoPlayer";

const STATE_KEY = "__cool_video_player_widget_state";
const NODE_STATES = new Map();
let EXECUTED_HANDLER = null;
let EXECUTED_API = null;

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
        output_payload?.video_entries,
        output_payload?.videos,
        output_payload?.video,
    ];
    for (const candidate of candidates) {
        const entries = Array.isArray(candidate) ? candidate : [candidate];
        for (const entry of entries) {
            if (typeof entry === "string" && entry.trim().length > 0) {
                return { source_url: entry.trim() };
            }
            if (!entry || typeof entry !== "object") {
                continue;
            }
            const source_url = String(entry.source_url ?? entry.url ?? "").trim();
            if (source_url.length > 0) {
                return { source_url };
            }
            const fallback_url = build_view_url(entry);
            if (fallback_url.length > 0) {
                return { source_url: fallback_url };
            }
        }
    }
    return null;
}

function set_status(widget_state, text) {
    if (widget_state?.status_element) {
        widget_state.status_element.textContent = text;
    }
}

function stop_video_preview(widget_state) {
    if (!widget_state || widget_state.stopped) {
        return;
    }
    widget_state.stopped = true;

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
    const render = () => {
        if (widget_state.stopped) {
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
        set_status(widget_state, "No video preview data available.");
        return false;
    }

    const source_url = String(video_entry.source_url).trim();
    if (source_url.length === 0) {
        set_status(widget_state, "No video preview data available.");
        return false;
    }

    if (widget_state.video_element.src !== source_url) {
        widget_state.video_element.src = source_url;
        if (typeof widget_state.video_element.load === "function") {
            widget_state.video_element.load();
        }
    }

    set_status(widget_state, "Rendering video preview...");
    if (typeof widget_state.video_element.play === "function") {
        const play_result = widget_state.video_element.play();
        if (play_result && typeof play_result.then === "function") {
            play_result
                .then(() => {
                    set_status(widget_state, "");
                })
                .catch((error) => {
                    const error_message =
                        error && error.message ? error.message : "Unable to autoplay preview.";
                    set_status(widget_state, `Preview unavailable: ${error_message}`);
                });
        } else {
            set_status(widget_state, "");
        }
    } else {
        set_status(widget_state, "");
    }

    return true;
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
        const node_id = normalize_node_id(detail.node);
        if (node_id.length === 0) {
            return;
        }
        const widget_state = NODE_STATES.get(node_id);
        if (!widget_state) {
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
    request_animation_frame = globalThis.requestAnimationFrame,
    cancel_animation_frame = globalThis.cancelAnimationFrame,
    api_ref = globalThis.app?.api ?? null,
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

    const resolved_request_animation_frame =
        typeof request_animation_frame === "function"
            ? request_animation_frame
            : (callback) => globalThis.setTimeout(callback, 16);
    const resolved_cancel_animation_frame =
        typeof cancel_animation_frame === "function"
            ? cancel_animation_frame
            : (handle) => globalThis.clearTimeout(handle);

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
        borderRadius: "6px",
        background: "rgb(20, 24, 32)",
        aspectRatio: "16 / 9",
        display: "block",
    });
    container_element.appendChild(canvas_element);

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
    video_element.autoplay = true;
    video_element.playsInline = true;
    video_element.crossOrigin = "anonymous";

    const context =
        typeof canvas_element.getContext === "function"
            ? canvas_element.getContext("2d")
            : null;

    const widget_state = {
        widget,
        container_element,
        canvas_element,
        context,
        status_element,
        video_element,
        animation_handle: null,
        stopped: false,
        request_animation_frame: resolved_request_animation_frame,
        cancel_animation_frame: resolved_cancel_animation_frame,
    };
    node[STATE_KEY] = widget_state;
    NODE_STATES.set(normalize_node_id(node.id), widget_state);

    ensure_executed_listener(api_ref);
    start_video_preview_loop(widget_state);
    return widget_state;
}

export function unmount_video_player_widget_for_node(node) {
    const widget_state = node?.[STATE_KEY];
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
        request_animation_frame = globalThis.requestAnimationFrame,
        cancel_animation_frame = globalThis.cancelAnimationFrame,
        api_ref = app_ref?.api ?? null,
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
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                unmount_video_player_widget_for_node(this);
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
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
