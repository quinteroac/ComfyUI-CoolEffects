export const EXTENSION_NAME = "Comfy.CoolEffects.TextOverlay";

const STATE_KEY = "__cool_text_overlay_widget_state";
const VIDEO_WIDGET_NAMES = new Set([
    "text",
    "font_family",
    "font_size",
    "color",
    "font_weight",
    "pos_x",
    "pos_y",
    "align",
    "opacity",
    "fragments",
]);
const DEFAULT_PREVIEW_WIDTH = 320;
const DEFAULT_PREVIEW_HEIGHT = 180;
const PREVIEW_CHROME_HEIGHT = 44;
const VIDEO_OUTPUT_BY_NODE_ID = new Map();
const NODE_STATES = new Map();
const INPUT_TYPE = 1;
const VIDEO_INPUT_NAME = "video";
let EXECUTED_HANDLER = null;
let EXECUTED_API = null;

function normalize_node_id(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value);
}

function clamp(value, min_value, max_value) {
    return Math.min(max_value, Math.max(min_value, value));
}

function find_widget(node, name) {
    return node?.widgets?.find((widget) => widget?.name === name) ?? null;
}

function widget_string(node, name, default_value = "") {
    const value = find_widget(node, name)?.value;
    if (value === undefined || value === null) {
        return default_value;
    }
    return String(value);
}

function widget_number(node, name, default_value) {
    const value = Number(find_widget(node, name)?.value);
    if (Number.isFinite(value)) {
        return value;
    }
    return default_value;
}

function default_status(state, value) {
    if (state?.status_element) {
        state.status_element.textContent = value;
    }
}

function get_preview_display_width(state) {
    const node_width = Number(state?.node?.size?.[0]);
    if (Number.isFinite(node_width) && node_width > 48) {
        return Math.max(180, Math.round(node_width - 28));
    }
    return DEFAULT_PREVIEW_WIDTH;
}

export function update_preview_layout(state, source_width, source_height) {
    if (!state?.canvas_element) {
        return;
    }

    const safe_width = Math.max(1, Number(source_width) || DEFAULT_PREVIEW_WIDTH);
    const safe_height = Math.max(1, Number(source_height) || DEFAULT_PREVIEW_HEIGHT);
    const display_width = get_preview_display_width(state);
    const display_height = Math.max(100, Math.round((display_width * safe_height) / safe_width));

    state.preview_width = safe_width;
    state.preview_height = safe_height;
    state.display_height = display_height;
    state.canvas_element.style.aspectRatio = `${safe_width} / ${safe_height}`;

    if (state.widget) {
        state.widget.computeSize = () => [display_width, display_height + PREVIEW_CHROME_HEIGHT];
    }

    const node = state.node;
    const desired_width = Math.max(Number(node?.size?.[0]) || 0, display_width + 16);
    const desired_height = Math.max(Number(node?.size?.[1]) || 0, display_height + 76);
    if (node && typeof node.setSize === "function") {
        node.setSize([desired_width, desired_height]);
    } else if (node) {
        node.size = [desired_width, desired_height];
    }
    node?.setDirtyCanvas?.(true, true);
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

export function extract_video_entry(output_payload) {
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

function parse_color(value, fallback) {
    const text = String(value ?? "").trim();
    if (/^#[0-9a-fA-F]{6}$/.test(text) || /^#[0-9a-fA-F]{3}$/.test(text)) {
        return text;
    }
    return fallback;
}

export function normalize_overlay_fragments(node) {
    const default_fragment = {
        text: widget_string(node, "text", "Cool Text"),
        font_size: Math.round(clamp(widget_number(node, "font_size", 48), 8, 512)),
        font_family: widget_string(node, "font_family", "Arial"),
        font_weight: widget_string(node, "font_weight", "normal").toLowerCase() === "bold" ? "bold" : "normal",
        color: parse_color(widget_string(node, "color", "#ffffff"), "#ffffff"),
    };
    const raw_fragments = widget_string(node, "fragments", "[]").trim();
    if (raw_fragments.length === 0 || raw_fragments === "[]") {
        return [default_fragment];
    }

    let parsed = null;
    try {
        parsed = JSON.parse(raw_fragments);
    } catch (_error) {
        return [default_fragment];
    }
    if (!Array.isArray(parsed) || parsed.length === 0) {
        return [default_fragment];
    }

    const rich_fragments = [];
    for (const fragment of parsed) {
        if (!fragment || typeof fragment !== "object") {
            continue;
        }
        const text = String(fragment.text ?? "");
        if (text.length === 0) {
            continue;
        }
        rich_fragments.push({
            text,
            font_size: Math.round(
                clamp(
                    Number(fragment.font_size ?? default_fragment.font_size) || default_fragment.font_size,
                    8,
                    512,
                ),
            ),
            font_family: String(fragment.font_family ?? default_fragment.font_family),
            font_weight:
                String(fragment.font_weight ?? default_fragment.font_weight).toLowerCase() === "bold"
                    ? "bold"
                    : "normal",
            color: parse_color(fragment.color ?? default_fragment.color, default_fragment.color),
        });
    }
    return rich_fragments.length > 0 ? rich_fragments : [default_fragment];
}

export function render_overlay_text(state) {
    const context = state?.context;
    const canvas = state?.canvas_element;
    const node = state?.node;
    if (!context || !canvas || !node) {
        return;
    }

    const width = canvas.width || state.preview_width || DEFAULT_PREVIEW_WIDTH;
    const height = canvas.height || state.preview_height || DEFAULT_PREVIEW_HEIGHT;
    const fragments = normalize_overlay_fragments(node).filter((fragment) => fragment.text.length > 0);
    if (fragments.length === 0) {
        return;
    }

    const align = widget_string(node, "align", "center");
    const opacity = clamp(widget_number(node, "opacity", 1.0), 0.0, 1.0);
    const anchor_x = clamp(widget_number(node, "pos_x", 0.5), 0.0, 1.0) * width;
    const baseline_y = clamp(widget_number(node, "pos_y", 0.1), 0.0, 1.0) * height;

    const widths = fragments.map((fragment) => {
        context.font = `${fragment.font_weight} ${fragment.font_size}px ${fragment.font_family}`;
        return Number(context.measureText(fragment.text)?.width ?? 0);
    });
    const total_width = widths.reduce((acc, value) => acc + value, 0);

    let cursor_x = anchor_x;
    if (align === "center") {
        cursor_x = anchor_x - total_width / 2.0;
    } else if (align === "right") {
        cursor_x = anchor_x - total_width;
    }

    context.save?.();
    context.globalAlpha = opacity;
    context.textBaseline = "alphabetic";
    for (let index = 0; index < fragments.length; index++) {
        const fragment = fragments[index];
        context.font = `${fragment.font_weight} ${fragment.font_size}px ${fragment.font_family}`;
        context.fillStyle = fragment.color;
        context.fillText(fragment.text, cursor_x, baseline_y);
        cursor_x += widths[index];
    }
    context.restore?.();
}

export function render_preview_frame(state) {
    const context = state?.context;
    const canvas = state?.canvas_element;
    const video_element = state?.video_element;
    if (!context || !canvas || !video_element) {
        return false;
    }

    if (
        Number(video_element.readyState) < 2 ||
        Number(video_element.videoWidth) <= 0 ||
        Number(video_element.videoHeight) <= 0
    ) {
        return false;
    }

    update_preview_layout(state, video_element.videoWidth, video_element.videoHeight);
    if (canvas.width !== video_element.videoWidth || canvas.height !== video_element.videoHeight) {
        canvas.width = video_element.videoWidth;
        canvas.height = video_element.videoHeight;
    }

    context.clearRect?.(0, 0, canvas.width, canvas.height);
    context.drawImage(video_element, 0, 0, canvas.width, canvas.height);
    render_overlay_text(state);
    default_status(state, "");
    return true;
}

function apply_video_entry(state, video_entry) {
    const source_url = String(video_entry?.source_url ?? "").trim();
    if (source_url.length === 0) {
        default_status(state, "Connect a VIDEO input to preview.");
        return;
    }
    if (state.video_source_url === source_url) {
        render_preview_frame(state);
        return;
    }
    state.video_source_url = source_url;
    state.video_element.src = source_url;
    if (typeof state.video_element.load === "function") {
        state.video_element.load();
    }
    default_status(state, "Loading connected VIDEO preview...");
}

function resolve_connected_video_entry(state) {
    const node = state?.node;
    const graph = node?.graph;
    const video_input = node?.inputs?.find((input) => input?.name === VIDEO_INPUT_NAME);
    const link_id = video_input?.link;
    if (!graph || link_id === null || link_id === undefined) {
        return null;
    }
    const links = graph.links ?? {};
    const link = links[link_id];
    const origin_id = normalize_node_id(link?.origin_id);
    if (origin_id.length === 0) {
        return null;
    }
    return VIDEO_OUTPUT_BY_NODE_ID.get(origin_id) ?? null;
}

export function patch_preview_widget_callbacks(node, state) {
    for (const widget of node?.widgets ?? []) {
        if (!VIDEO_WIDGET_NAMES.has(widget?.name) || widget.__cool_text_overlay_patched) {
            continue;
        }
        widget.__cool_text_overlay_patched = true;
        const previous_callback = widget.callback;
        widget.callback = function patched_widget_callback(value) {
            if (typeof previous_callback === "function") {
                previous_callback.call(this, value);
            }
            render_preview_frame(state);
            state.node?.setDirtyCanvas?.(true, true);
        };
    }
}

function register_widget_state(node, state) {
    const node_id = normalize_node_id(node?.id);
    state.node_id = node_id;
    if (node_id.length > 0) {
        NODE_STATES.set(node_id, state);
    }
}

function ensure_executed_listener(api_ref) {
    if (!api_ref || typeof api_ref.addEventListener !== "function") {
        return;
    }
    if (EXECUTED_HANDLER && EXECUTED_API === api_ref) {
        return;
    }
    if (EXECUTED_HANDLER && EXECUTED_API && typeof EXECUTED_API.removeEventListener === "function") {
        EXECUTED_API.removeEventListener("executed", EXECUTED_HANDLER);
    }

    EXECUTED_API = api_ref;
    EXECUTED_HANDLER = (event) => {
        const detail = event?.detail ?? {};
        const node_id = normalize_node_id(detail.node ?? detail.node_id);
        const video_entry = extract_video_entry(detail.output ?? {});
        if (!video_entry || node_id.length === 0) {
            return;
        }
        VIDEO_OUTPUT_BY_NODE_ID.set(node_id, video_entry);
        const state = NODE_STATES.get(node_id);
        if (state) {
            apply_video_entry(state, video_entry);
        }
    };
    api_ref.addEventListener("executed", EXECUTED_HANDLER);
}

function maybe_remove_executed_listener() {
    if (NODE_STATES.size > 0) {
        return;
    }
    if (EXECUTED_API && EXECUTED_HANDLER && typeof EXECUTED_API.removeEventListener === "function") {
        EXECUTED_API.removeEventListener("executed", EXECUTED_HANDLER);
    }
    EXECUTED_API = null;
    EXECUTED_HANDLER = null;
}

function mount_text_overlay_widget({
    node,
    document_ref = globalThis.document,
    api_ref = null,
} = {}) {
    if (!node || typeof node.addDOMWidget !== "function") {
        return null;
    }
    if (!document_ref || typeof document_ref.createElement !== "function") {
        throw new Error("Missing document reference for CoolTextOverlay widget");
    }

    const container = document_ref.createElement("div");
    Object.assign(container.style, {
        display: "grid",
        gridTemplateRows: "auto auto",
        gap: "6px",
        width: "100%",
        padding: "6px 8px 8px",
        boxSizing: "border-box",
    });

    const canvas = document_ref.createElement("canvas");
    Object.assign(canvas.style, {
        width: "100%",
        height: "auto",
        display: "block",
        borderRadius: "6px",
        background: "#171b22",
        aspectRatio: `${DEFAULT_PREVIEW_WIDTH} / ${DEFAULT_PREVIEW_HEIGHT}`,
    });

    const status = document_ref.createElement("div");
    Object.assign(status.style, {
        fontSize: "11px",
        lineHeight: "1.35",
        color: "#97a4b3",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
        minWidth: "0",
    });
    status.textContent = "Connect a VIDEO input to preview.";

    container.append(canvas, status);

    const widget = node.addDOMWidget("text_overlay_preview", "div", container, {
        serialize: false,
        hideOnZoom: false,
    });

    const context = canvas.getContext("2d");
    const video_element = document_ref.createElement("video");
    video_element.preload = "auto";
    video_element.muted = true;
    video_element.playsInline = true;
    video_element.crossOrigin = "anonymous";

    const state = {
        node,
        widget,
        container_element: container,
        canvas_element: canvas,
        context,
        status_element: status,
        video_element,
        video_source_url: "",
        preview_width: DEFAULT_PREVIEW_WIDTH,
        preview_height: DEFAULT_PREVIEW_HEIGHT,
    };

    video_element.addEventListener("loadedmetadata", () => {
        update_preview_layout(state, video_element.videoWidth, video_element.videoHeight);
    });
    video_element.addEventListener("loadeddata", () => {
        if (typeof video_element.pause === "function") {
            video_element.pause();
        }
        try {
            if (typeof video_element.currentTime === "number") {
                video_element.currentTime = 0;
            }
        } catch (_error) {
            // Keep the best loaded frame for preview if seek is blocked.
        }
        render_preview_frame(state);
    });
    video_element.addEventListener("seeked", () => {
        render_preview_frame(state);
    });
    video_element.addEventListener("error", () => {
        default_status(state, "Unable to decode connected VIDEO preview.");
    });

    node[STATE_KEY] = state;
    register_widget_state(node, state);
    patch_preview_widget_callbacks(node, state);
    update_preview_layout(state, DEFAULT_PREVIEW_WIDTH, DEFAULT_PREVIEW_HEIGHT);

    const linked_video_entry = resolve_connected_video_entry(state);
    if (linked_video_entry) {
        apply_video_entry(state, linked_video_entry);
    }

    ensure_executed_listener(api_ref);
    return state;
}

function unmount_text_overlay_widget(node) {
    const state = node?.[STATE_KEY];
    if (!state) {
        return;
    }
    if (state.video_element) {
        if (typeof state.video_element.pause === "function") {
            state.video_element.pause();
        }
        state.video_element.src = "";
        if (typeof state.video_element.load === "function") {
            state.video_element.load();
        }
    }
    NODE_STATES.delete(normalize_node_id(node?.id));
    maybe_remove_executed_listener();
}

export function register_comfy_extension(app_ref, { document_ref = globalThis.document } = {}) {
    if (!app_ref || typeof app_ref.registerExtension !== "function") {
        return false;
    }

    app_ref.registerExtension({
        name: EXTENSION_NAME,
        async beforeRegisterNodeDef(nodeType, nodeData) {
            if (nodeData?.name !== "CoolTextOverlay") {
                return;
            }
            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_executed = nodeType.prototype.onExecuted;
            const previous_on_connections_change = nodeType.prototype.onConnectionsChange;

            nodeType.prototype.onNodeCreated = function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                mount_text_overlay_widget({
                    node: this,
                    document_ref,
                    api_ref: app_ref?.api ?? null,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                unmount_text_overlay_widget(this);
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
            };

            nodeType.prototype.onExecuted = function onExecuted(output) {
                if (typeof previous_on_executed === "function") {
                    previous_on_executed.apply(this, arguments);
                }
                const state = this?.[STATE_KEY];
                const entry = extract_video_entry(output ?? {});
                if (state && entry) {
                    apply_video_entry(state, entry);
                }
            };

            nodeType.prototype.onConnectionsChange = function onConnectionsChange(
                slot_type,
                slot_index,
                connected,
                link_info,
                io_slot,
            ) {
                if (typeof previous_on_connections_change === "function") {
                    previous_on_connections_change.apply(this, arguments);
                }
                const state = this?.[STATE_KEY];
                if (!state) {
                    return;
                }

                const changed_video_input =
                    slot_type === INPUT_TYPE &&
                    (io_slot?.name === VIDEO_INPUT_NAME ||
                        this?.inputs?.[slot_index]?.name === VIDEO_INPUT_NAME);
                if (!changed_video_input) {
                    return;
                }

                if (!connected) {
                    default_status(state, "Connect a VIDEO input to preview.");
                    return;
                }

                const linked_entry = resolve_connected_video_entry(state);
                if (linked_entry) {
                    apply_video_entry(state, linked_entry);
                } else {
                    default_status(state, "Run upstream video node once to seed preview.");
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
