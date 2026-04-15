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
export const PRETEXT_CDN_URL = "https://esm.sh/@chenglou/pretext/rich-inline";
export const PRETEXT_VENDOR_URL = new URL("./vendor/pretext-rich-inline.mjs", import.meta.url).href;
const PRETEXT_IMPORT_CANDIDATES = [PRETEXT_CDN_URL, PRETEXT_VENDOR_URL];
let EXECUTED_HANDLER = null;
let EXECUTED_API = null;
let PRETEXT_IMPORT_PROMISE = null;
let PRETEXT_MODULE_CACHE = null;
let PRETEXT_DYNAMIC_IMPORT = null;

function default_dynamic_import(url) {
    return import(url);
}

function get_dynamic_importer() {
    if (typeof PRETEXT_DYNAMIC_IMPORT === "function") {
        return PRETEXT_DYNAMIC_IMPORT;
    }
    return default_dynamic_import;
}

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

    const editor_height = Math.max(0, Number(state?.fragment_editor_height) || 0);
    if (state.widget) {
        state.widget.computeSize = () => [
            display_width,
            display_height + PREVIEW_CHROME_HEIGHT + editor_height,
        ];
    }

    const node = state.node;
    const desired_width = Math.max(Number(node?.size?.[0]) || 0, display_width + 16);
    const desired_height = Math.max(Number(node?.size?.[1]) || 0, display_height + 76 + editor_height);
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

function build_default_fragment(node) {
    return {
        text: widget_string(node, "text", "Cool Text"),
        font_size: Math.round(clamp(widget_number(node, "font_size", 48), 8, 512)),
        font_family: widget_string(node, "font_family", "Arial"),
        font_weight: widget_string(node, "font_weight", "normal").toLowerCase() === "bold" ? "bold" : "normal",
        color: parse_color(widget_string(node, "color", "#ffffff"), "#ffffff"),
    };
}

function normalize_fragment_style(fragment, default_fragment) {
    return {
        text: String(fragment?.text ?? ""),
        font_size: Math.round(
            clamp(
                Number(fragment?.font_size ?? default_fragment.font_size) || default_fragment.font_size,
                8,
                512,
            ),
        ),
        font_family: String(fragment?.font_family ?? default_fragment.font_family),
        font_weight:
            String(fragment?.font_weight ?? default_fragment.font_weight).toLowerCase() === "bold"
                ? "bold"
                : "normal",
        color: parse_color(fragment?.color ?? default_fragment.color, default_fragment.color),
    };
}

function parse_fragment_list_widget_value(node) {
    const raw_fragments = widget_string(node, "fragments", "[]").trim();
    if (raw_fragments.length === 0 || raw_fragments === "[]") {
        return [];
    }
    try {
        const parsed = JSON.parse(raw_fragments);
        return Array.isArray(parsed) ? parsed : [];
    } catch (_error) {
        return [];
    }
}

export function serialize_fragment_editor_fragments(fragments) {
    const normalized = (Array.isArray(fragments) ? fragments : []).map((fragment) => ({
        text: String(fragment?.text ?? ""),
        font_size: Math.round(clamp(Number(fragment?.font_size) || 48, 8, 512)),
        font_family: String(fragment?.font_family ?? "Arial"),
        font_weight: String(fragment?.font_weight ?? "normal").toLowerCase() === "bold" ? "bold" : "normal",
        color: parse_color(fragment?.color, "#ffffff"),
    }));
    return JSON.stringify(normalized);
}

export function read_fragment_editor_fragments(node) {
    const default_fragment = build_default_fragment(node);
    const parsed = parse_fragment_list_widget_value(node);
    const normalized = parsed
        .filter((fragment) => fragment && typeof fragment === "object")
        .map((fragment) => normalize_fragment_style(fragment, default_fragment));
    return normalized.length > 0 ? normalized : [default_fragment];
}

function to_canvas_font(fragment) {
    return `${fragment.font_weight} ${fragment.font_size}px ${fragment.font_family}`;
}

function build_rich_inline_specs(fragments) {
    return fragments.map((fragment) => ({
        text: fragment.text,
        font: to_canvas_font(fragment),
    }));
}

async function import_pretext_module(dynamic_importer) {
    let last_error = null;
    for (const source_url of PRETEXT_IMPORT_CANDIDATES) {
        try {
            return await dynamic_importer(source_url);
        } catch (error) {
            last_error = error;
        }
    }
    throw last_error ?? new Error("Failed to import pretext rich-inline module");
}

export async function load_pretext_rich_inline_module(dynamic_importer = get_dynamic_importer()) {
    const use_cache = dynamic_importer === get_dynamic_importer();
    if (use_cache && PRETEXT_MODULE_CACHE) {
        return PRETEXT_MODULE_CACHE;
    }
    if (use_cache && PRETEXT_IMPORT_PROMISE) {
        return PRETEXT_IMPORT_PROMISE;
    }

    const load_promise = import_pretext_module(dynamic_importer)
        .then((module_ref) => {
            const module_obj = module_ref?.default ?? module_ref;
            if (use_cache) {
                PRETEXT_MODULE_CACHE = module_obj;
            }
            return module_obj;
        })
        .finally(() => {
            if (use_cache) {
                PRETEXT_IMPORT_PROMISE = null;
            }
        });
    if (use_cache) {
        PRETEXT_IMPORT_PROMISE = load_promise;
    }
    return load_promise;
}

function measure_rich_inline_widths_with_pretext_module(pretext_module, fragments, context) {
    if (
        typeof pretext_module?.prepareRichInline !== "function" ||
        typeof pretext_module?.layoutNextRichInlineLineRange !== "function"
    ) {
        throw new Error("Pretext rich-inline API is unavailable");
    }
    const specs = build_rich_inline_specs(fragments);
    const prepared = pretext_module.prepareRichInline(specs, context);
    const line_range = pretext_module.layoutNextRichInlineLineRange(prepared, Number.POSITIVE_INFINITY);
    if (!line_range || !Array.isArray(line_range.fragments)) {
        return null;
    }
    return line_range.fragments.map((entry) => {
        const occupied_width = Number(entry?.occupiedWidth);
        return Number.isFinite(occupied_width) ? Math.max(0, occupied_width) : 0;
    });
}

export async function measure_rich_inline_widths_with_pretext(fragments, context) {
    const pretext_module = await load_pretext_rich_inline_module();
    return measure_rich_inline_widths_with_pretext_module(pretext_module, fragments, context);
}

function get_fragment_layout_key(fragments) {
    return JSON.stringify(
        fragments.map((fragment) => ({
            text: fragment.text,
            font_size: fragment.font_size,
            font_family: fragment.font_family,
            font_weight: fragment.font_weight,
            color: fragment.color,
        })),
    );
}

function request_pretext_fragment_widths(state, fragments, context) {
    if (!state) {
        return null;
    }
    const layout_key = get_fragment_layout_key(fragments);
    state.pretext_widths_by_key = state.pretext_widths_by_key ?? new Map();
    state.pretext_requests_by_key = state.pretext_requests_by_key ?? new Map();
    if (state.pretext_widths_by_key.has(layout_key)) {
        return state.pretext_widths_by_key.get(layout_key);
    }
    if (state.pretext_requests_by_key.has(layout_key)) {
        return null;
    }
    if (PRETEXT_MODULE_CACHE) {
        try {
            const widths = measure_rich_inline_widths_with_pretext_module(PRETEXT_MODULE_CACHE, fragments, context);
            if (Array.isArray(widths) && widths.length === fragments.length) {
                state.pretext_widths_by_key.set(layout_key, widths);
                return widths;
            }
        } catch (_error) {
            // Continue with async request fallback.
        }
    }

    const request = measure_rich_inline_widths_with_pretext(fragments, context)
        .then((widths) => {
            if (Array.isArray(widths) && widths.length === fragments.length) {
                state.pretext_widths_by_key.set(layout_key, widths);
            }
        })
        .catch(() => {
            // Keep canvas fallback widths if pretext cannot load.
        })
        .finally(() => {
            state.pretext_requests_by_key.delete(layout_key);
            render_preview_frame(state);
        });
    state.pretext_requests_by_key.set(layout_key, request);
    return null;
}

export function normalize_overlay_fragments(node) {
    const default_fragment = build_default_fragment(node);
    const rich_fragments = read_fragment_editor_fragments(node).filter(
        (fragment) => String(fragment?.text ?? "").length > 0,
    );
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

    const pretext_widths = request_pretext_fragment_widths(state, fragments, context);
    const widths = fragments.map((fragment, index) => {
        if (Array.isArray(pretext_widths)) {
            const pretext_width = Number(pretext_widths[index]);
            if (Number.isFinite(pretext_width)) {
                return Math.max(0, pretext_width);
            }
        }
        context.font = to_canvas_font(fragment);
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
        context.font = to_canvas_font(fragment);
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

function sync_fragment_editor_to_widget(state) {
    const node = state?.node;
    const fragments_widget = find_widget(node, "fragments");
    if (!fragments_widget) {
        render_preview_frame(state);
        node?.setDirtyCanvas?.(true, true);
        return;
    }
    const serialized_fragments = serialize_fragment_editor_fragments(state.fragment_rows);
    fragments_widget.value = serialized_fragments;
    state.fragment_editor_updating_widget = true;
    try {
        if (typeof fragments_widget.callback === "function") {
            fragments_widget.callback.call(fragments_widget, serialized_fragments);
        } else {
            render_preview_frame(state);
            node?.setDirtyCanvas?.(true, true);
        }
    } finally {
        state.fragment_editor_updating_widget = false;
    }
}

function update_fragment_remove_buttons(state) {
    const buttons = state?.fragment_remove_buttons ?? [];
    const disable_remove = buttons.length <= 1;
    for (const button of buttons) {
        button.disabled = disable_remove;
        button.title = disable_remove ? "At least one fragment is required." : "Remove this fragment";
    }
}

function render_fragment_editor_rows(state, document_ref = globalThis.document) {
    const rows_container = state?.fragment_rows_container;
    if (!rows_container || !document_ref) {
        return;
    }
    rows_container.textContent = "";
    state.fragment_remove_buttons = [];

    state.fragment_rows.forEach((fragment, index) => {
        const row = document_ref.createElement("div");
        row.setAttribute("data-fragment-row", String(index));
        Object.assign(row.style, {
            display: "grid",
            gridTemplateColumns: "minmax(0,1fr) 80px 70px 92px 70px",
            gap: "6px",
            alignItems: "center",
            minWidth: "0",
        });

        const text_input = document_ref.createElement("input");
        text_input.type = "text";
        text_input.value = fragment.text;
        text_input.placeholder = "Text";
        text_input.setAttribute("data-fragment-field", "text");
        Object.assign(text_input.style, {
            minWidth: "0",
        });
        text_input.addEventListener("input", () => {
            state.fragment_rows[index].text = String(text_input.value ?? "");
            sync_fragment_editor_to_widget(state);
        });

        const color_input = document_ref.createElement("input");
        color_input.type = "color";
        color_input.value = parse_color(fragment.color, "#ffffff");
        color_input.setAttribute("data-fragment-field", "color");
        color_input.addEventListener("input", () => {
            state.fragment_rows[index].color = parse_color(color_input.value, "#ffffff");
            sync_fragment_editor_to_widget(state);
        });

        const size_input = document_ref.createElement("input");
        size_input.type = "number";
        size_input.value = String(fragment.font_size);
        size_input.min = "8";
        size_input.max = "512";
        size_input.step = "1";
        size_input.setAttribute("data-fragment-field", "font_size");
        size_input.addEventListener("input", () => {
            state.fragment_rows[index].font_size = Math.round(clamp(Number(size_input.value) || 48, 8, 512));
            size_input.value = String(state.fragment_rows[index].font_size);
            sync_fragment_editor_to_widget(state);
        });

        const family_input = document_ref.createElement("input");
        family_input.type = "text";
        family_input.value = fragment.font_family;
        family_input.placeholder = "Font family";
        family_input.setAttribute("data-fragment-field", "font_family");
        family_input.addEventListener("input", () => {
            state.fragment_rows[index].font_family = String(family_input.value ?? "");
            sync_fragment_editor_to_widget(state);
        });

        const trailing_actions = document_ref.createElement("div");
        Object.assign(trailing_actions.style, {
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "6px",
            minWidth: "0",
        });

        const weight_select = document_ref.createElement("select");
        weight_select.setAttribute("data-fragment-field", "font_weight");
        const normal_option = document_ref.createElement("option");
        normal_option.value = "normal";
        normal_option.textContent = "Normal";
        const bold_option = document_ref.createElement("option");
        bold_option.value = "bold";
        bold_option.textContent = "Bold";
        weight_select.append(normal_option, bold_option);
        weight_select.value = fragment.font_weight === "bold" ? "bold" : "normal";
        weight_select.addEventListener("change", () => {
            state.fragment_rows[index].font_weight = weight_select.value === "bold" ? "bold" : "normal";
            sync_fragment_editor_to_widget(state);
        });

        const remove_button = document_ref.createElement("button");
        remove_button.type = "button";
        remove_button.textContent = "Remove";
        remove_button.setAttribute("data-fragment-field", "remove");
        remove_button.addEventListener("click", () => {
            if (state.fragment_rows.length <= 1) {
                update_fragment_remove_buttons(state);
                return;
            }
            state.fragment_rows.splice(index, 1);
            render_fragment_editor_rows(state, document_ref);
            sync_fragment_editor_to_widget(state);
        });

        state.fragment_remove_buttons.push(remove_button);
        trailing_actions.append(weight_select, remove_button);
        row.append(text_input, color_input, size_input, family_input, trailing_actions);
        rows_container.append(row);
    });

    update_fragment_remove_buttons(state);
    state.fragment_editor_height = 68 + state.fragment_rows.length * 36;
    update_preview_layout(state, state.preview_width || DEFAULT_PREVIEW_WIDTH, state.preview_height || DEFAULT_PREVIEW_HEIGHT);
}

function sync_fragment_editor_from_widget(state, document_ref = globalThis.document) {
    state.fragment_rows = read_fragment_editor_fragments(state.node);
    render_fragment_editor_rows(state, document_ref);
}

function mount_fragment_editor(state, document_ref) {
    const panel = document_ref.createElement("div");
    panel.setAttribute("data-fragment-editor", "true");
    Object.assign(panel.style, {
        display: "grid",
        gap: "6px",
        padding: "8px",
        borderRadius: "8px",
        background: "#10151d",
        border: "1px solid #273244",
    });

    const panel_header = document_ref.createElement("div");
    panel_header.textContent = "Fragments";
    Object.assign(panel_header.style, {
        fontSize: "11px",
        fontWeight: "600",
        color: "#c4d5ea",
        letterSpacing: "0.02em",
    });

    const rows_container = document_ref.createElement("div");
    Object.assign(rows_container.style, {
        display: "grid",
        gap: "6px",
    });

    const add_button = document_ref.createElement("button");
    add_button.type = "button";
    add_button.textContent = "Add fragment";
    Object.assign(add_button.style, {
        justifySelf: "start",
    });
    add_button.addEventListener("click", () => {
        state.fragment_rows.push(build_default_fragment(state.node));
        render_fragment_editor_rows(state, document_ref);
        sync_fragment_editor_to_widget(state);
    });

    panel.append(panel_header, rows_container, add_button);
    state.fragment_rows_container = rows_container;
    state.fragment_add_button = add_button;
    state.fragment_rows = read_fragment_editor_fragments(state.node);
    render_fragment_editor_rows(state, document_ref);
    sync_fragment_editor_to_widget(state);
    return panel;
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
            if (widget.name === "fragments" && !state.fragment_editor_updating_widget) {
                sync_fragment_editor_from_widget(state);
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

export function mount_text_overlay_widget({
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
        gridTemplateRows: "auto auto auto",
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
        fragment_rows: [],
        fragment_remove_buttons: [],
        fragment_editor_updating_widget: false,
    };
    const fragment_editor = mount_fragment_editor(state, document_ref);
    container.append(fragment_editor, canvas, status);

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

export function set_pretext_dynamic_import_for_tests(import_fn) {
    PRETEXT_DYNAMIC_IMPORT = typeof import_fn === "function" ? import_fn : null;
    PRETEXT_IMPORT_PROMISE = null;
    PRETEXT_MODULE_CACHE = null;
}

void auto_register_comfy_extension();
