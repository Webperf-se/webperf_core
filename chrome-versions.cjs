/* 
 * USED FOR SITESPEED TEST (TO collect software and javascript used)!!!
 */
module.exports = async function (context, commands) {
    // cdpClient = commands.cdp.engineDelegate.getCDPClient()
    // https://chromedevtools.github.io/devtools-protocol/tot/Storage/#method-getCookies
    // bodyResult = await cdpClient.send('Runtime.evaluate', {
    //     'expression': 'document.location.href'
    // });
    // await commands.wait.byTime(20000);

    // bodyResult = await cdpClient.send('Runtime.evaluate', {
    //     'allowUnsafeEvalBlockedByCSP': true,
    //     'expression': '"jQuery" in window && "fn" in window.jQuery && "jquery" in window.jQuery.fn ? window.jQuery.fn.jquery : ""'
    // });
    // commands.wait.byCondition(commands.wait.byPageToComplete, 5000);
    try {
        // Fix for exception thrown on some pages where this function doesn't trigger until timeout: https://github.com/sitespeedio/browsertime/blob/main/lib/core/engine/command/wait.js#L126
        await commands.wait.byPageToComplete();
    } catch (error) {
        
    }

    core_js_versions = [];
    try {
        core_js_count = await commands.js.run('return "__core-js_shared__" in window && "versions" in window["__core-js_shared__"] ? window["__core-js_shared__"]["versions"].length : 0')
        for (let index = 0; index < core_js_count; index++) {
            value = await commands.js.run('return "__core-js_shared__" in window && "versions" in window["__core-js_shared__"] ? window["__core-js_shared__"]["versions"][' + index +']["version"] : -1')
            if (value.indexOf('ERROR') === -1) {
                core_js_versions.push(value);
            }
        }
    } catch (error) {
        console.error(error);
    }

    modernizr_versions = []
    try {
        modernizr_versions = await commands.js.run('return "Modernizr" in window && "_version" in window.Modernizr ? [window.Modernizr._version] : []');
    } catch (error) {
        console.error(error);
    }

    alpine_versions = []
    try {
        alpine_versions = await commands.js.run('return "Alpine" in window && "version" in window.Alpine ? [window.Alpine.version] : []');
    } catch (error) {
        console.error(error);
    }

    next_versions = []
    try {
        next_versions = await commands.js.run('return "next" in window && "version" in window.next ? [window.next.version] : []');
    } catch (error) {
        console.error(error);
    }

    jquery_versions = []
    try {
        tmp = await commands.js.run('return typeof jQuery !== "undefined"');
        tmp = await commands.js.run('return typeof jQuery !== "undefined" && typeof jQuery.prototype !== "undefined"');
        tmp = await commands.js.run('return typeof jQuery !== "undefined" && typeof jQuery.prototype !== "undefined" && jQuery.prototype.jquery !== "undefined"');
        jquery_versions = await commands.js.run('return typeof jQuery !== "undefined" && typeof jQuery.prototype !== "undefined" && jQuery.prototype.jquery !== "undefined" ? [jQuery.prototype.jquery] : []');

        // Add support for "jQuery running noConflict"
        tmp = await commands.js.run('return "jQuery" in window');
        if (tmp) {
            jquery_versions = await commands.js.run(
                [
                    "jquery_versions = []",
                    "for (x in window) {",
                    "if ((typeof(window[x]) === 'object' || typeof(window[x]) === 'function') && typeof (window[x]) !== 'undefined' && window[x] !== null) {",
                    "if (Object.keys(window[x]).indexOf('fn') !== -1) {",
                            "if (window[x] && 'jquery' in window[x]['fn']) {",
                                "jquery_versions.push(window[x]['fn']['jquery'])",
                            "}",
                        "}",
                    "}",
                    "}",
                    "return jquery_versions;"
                ].join('\r\n'));
        }
        if (jquery_versions === null || jquery_versions == {}) {
            jquery_versions = []
        }
    } catch (error) {
        console.error(error);
    }

    versions = {
        'jquery': [...new Set(jquery_versions)],
        'modernizr': [...new Set(modernizr_versions)],
        'core-js': [...new Set(core_js_versions)],
        'next.js': [...new Set(next_versions)],
        'alpinejs': [...new Set(alpine_versions)]
    }


    // window['__core-js_shared__'].versions

    // bodyResult = await commands.js.run('return { "jquery": "jQuery" in window && "fn" in window.jQuery && "jquery" in window.jQuery.fn ? window.jQuery.fn.jquery : ""}');
    // bodyResult = await cdpClient.send('Runtime.evaluate', {
    //     'expression': 'window.jQuery.fn.jquery'
    // });
    context.log.info('VERSIONS:START:', versions, 'VERSIONS:END');
}