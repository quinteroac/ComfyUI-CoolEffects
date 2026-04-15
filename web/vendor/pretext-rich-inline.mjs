function to_number(value, fallback = 0) {
    const numeric = Number(value);
    if (Number.isFinite(numeric)) {
        return numeric;
    }
    return fallback;
}

function create_measure_context() {
    const canvas = globalThis.document?.createElement?.("canvas");
    return canvas?.getContext?.("2d") ?? null;
}

export function prepareRichInline(items) {
    return {
        items: Array.isArray(items) ? items : [],
    };
}

export function layoutNextRichInlineLineRange(prepared, _maxWidth, _cursor) {
    const items = Array.isArray(prepared?.items) ? prepared.items : [];
    const context = create_measure_context();
    const fragments = items.map((item, index) => {
        const text = String(item?.text ?? "");
        const font = String(item?.font ?? "16px sans-serif");
        if (context) {
            context.font = font;
        }
        const text_width = to_number(context?.measureText?.(text)?.width, text.length * 8);
        const extra_width = to_number(item?.extraWidth, 0);
        return {
            itemIndex: index,
            gapBefore: 0,
            occupiedWidth: text_width + extra_width,
            start: { segmentIndex: 0, graphemeIndex: 0 },
            end: { segmentIndex: 0, graphemeIndex: text.length },
        };
    });
    return {
        fragments,
        width: fragments.reduce((acc, fragment) => acc + fragment.occupiedWidth, 0),
        end: {
            itemIndex: fragments.length,
            segmentIndex: 0,
            graphemeIndex: 0,
        },
    };
}
