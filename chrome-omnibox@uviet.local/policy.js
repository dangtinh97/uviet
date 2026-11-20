const CHROME_WINDOW_IDS = new Set([
    'google-chrome',
    'google-chrome-stable',
    'com.google.chrome',
]);

export function shouldBypass(source, inputPurpose, urlPurpose, window) {
    if (source?.type !== 'ibus' || !/^Bamboo(?:::|$)/.test(source.id))
        return false;
    if (inputPurpose !== urlPurpose)
        return false;
    return [window?.get_wm_class(), window?.get_gtk_application_id()]
        .some(id => id && CHROME_WINDOW_IDS.has(id.toLowerCase()));
}
