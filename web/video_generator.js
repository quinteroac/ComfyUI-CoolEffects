/**
 * ComfyUI extension for CoolVideoGenerator.
 *
 * Watches the `effect_count` INT widget and dynamically adds or removes
 * `effect_params_N` input slots on the node so the user can chain effects
 * without needing to pre-wire a fixed number of inputs.
 */

const EFFECT_PARAMS_TYPE = "EFFECT_PARAMS";
const EFFECT_INPUT_PREFIX = "effect_params_";

/** Return the `effect_count` widget, or null if not found. */
function get_effect_count_widget(node) {
    return node.widgets?.find((w) => w.name === "effect_count") ?? null;
}

/** Return the indices (in node.inputs) of all effect_params_N slots, sorted ascending. */
function get_effect_param_input_indices(node) {
    const indices = [];
    const inputs = node.inputs ?? [];
    for (let i = 0; i < inputs.length; i++) {
        if (inputs[i]?.name?.startsWith(EFFECT_INPUT_PREFIX)) {
            indices.push(i);
        }
    }
    return indices;
}

/**
 * Ensure the node has exactly `count` effect_params slots.
 * Adds slots at the end or removes trailing ones to match the target count.
 */
function sync_effect_param_inputs(node, count) {
    const target = Math.max(1, Math.min(8, Math.round(count)));
    const indices = get_effect_param_input_indices(node);
    const current = indices.length;

    if (target === current) return;

    if (target > current) {
        // Add missing slots
        for (let i = current + 1; i <= target; i++) {
            node.addInput(`${EFFECT_INPUT_PREFIX}${i}`, EFFECT_PARAMS_TYPE);
        }
    } else {
        // Remove trailing slots (highest indices first to keep indices valid)
        const sorted_desc = [...indices].sort((a, b) => b - a);
        let removed = 0;
        for (const slot_index of sorted_desc) {
            if (current - removed <= target) break;
            const input = node.inputs[slot_index];
            // Disconnect any live link before removing
            if (input?.link != null && node.graph) {
                node.graph.removeLink(input.link);
            }
            node.removeInput(slot_index);
            removed++;
        }
    }

    node.setDirtyCanvas?.(true, true);
}

async function register_video_generator_extension() {
    let app;
    try {
        const mod = await import("../../scripts/app.js");
        app = mod.app;
    } catch {
        app = globalThis.app ?? null;
    }

    if (!app || typeof app.registerExtension !== "function") return;

    app.registerExtension({
        name: "Comfy.CoolEffects.VideoGenerator",

        async beforeRegisterNodeDef(nodeType, nodeData) {
            if (nodeData?.name !== "CoolVideoGenerator") return;

            const original_onNodeCreated = nodeType.prototype.onNodeCreated;
            const original_onConfigure = nodeType.prototype.onConfigure;

            nodeType.prototype.onNodeCreated = function () {
                if (typeof original_onNodeCreated === "function") {
                    original_onNodeCreated.apply(this, arguments);
                }
                _setup_effect_count_widget(this);
            };

            // onConfigure is called when a workflow is loaded from JSON.
            // LiteGraph restores serialised inputs automatically, but we still
            // need to wire up the widget callback for the restored node.
            nodeType.prototype.onConfigure = function (info) {
                if (typeof original_onConfigure === "function") {
                    original_onConfigure.apply(this, arguments);
                }
                _setup_effect_count_widget(this);
            };
        },
    });
}

/**
 * Hook the `effect_count` widget so changes drive input slot count.
 * Safe to call multiple times — skips if the widget is already patched.
 */
function _setup_effect_count_widget(node) {
    const count_widget = get_effect_count_widget(node);
    if (!count_widget || count_widget.__cool_patched) return;

    count_widget.__cool_patched = true;

    const original_callback = count_widget.callback;
    count_widget.callback = function (value) {
        if (typeof original_callback === "function") {
            original_callback.call(this, value);
        }
        sync_effect_param_inputs(node, value);
    };

    // Apply initial state immediately (covers both new nodes and loaded ones)
    sync_effect_param_inputs(node, count_widget.value ?? 1);
}

void register_video_generator_extension();
