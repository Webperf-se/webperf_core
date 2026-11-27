/* 
 * USED FOR SITESPEED TEST (TO test real no javascript gain)!!!
 * Right now sitespeed doesn't support blocking specific content type so this is our workaround
 */
// Reads --browsertime.webperf.<prefix>01..09 options, encoded as
// "<from>=<to>" with spaces as %20 and literal equals signs as %3D.
const getPluginOptionPairs = function (context, prefix) {
    const pairs = [];
    const options = (context.options && context.options.webperf) || {};
    for (let i = 1; i <= 9; i++) {
        const key = prefix + '0' + i;
        if (!(key in options)) {
            continue;
        }
        const parts = String(options[key]).replaceAll('%20', ' ').split('=');
        pairs.push([parts[0].replaceAll('%3D', '='), (parts[1] || '').replaceAll('%3D', '=')]);
    }
    return pairs;
};

module.exports = async function (context, commands) {
    // No options is the normal case (the baseline desktop and mobile runs),
    // so it is not logged.
    const headerOptions = getPluginOptionPairs(context, 'header')
        .map(([name, value]) => ({ name: name, value: value }));
    const htmlOptions = getPluginOptionPairs(context, 'HTML')
        .map(([replace, replaceWith]) => ({ replace: replace, replaceWith: replaceWith }));

    const cdpClient = commands.cdp.engineDelegate.getCDPClient()
    await cdpClient.send('Fetch.enable', {
        patterns: [
            {
                urlPattern: '*',
                resourceType: 'Document',
                requestStage: 'Response'
            }
        ]
    });

    // Continue a paused request without touching it. Used whenever we cannot
    // safely rewrite the response, so that one odd response never stalls the run.
    const releaseRequest = async function (requestId) {
        try {
            // Verified against Chromium 150: continueRequest releases a pause in
            // the Response stage too, so one call covers both stages.
            await cdpClient.send('Fetch.continueRequest', { requestId: requestId });
        } catch (err) {
            // Request already gone, or a future Chrome stopped accepting this in
            // the Response stage. Logged rather than swallowed, because a pause
            // that is never released stalls the page load until browsertime
            // times out.
            context.log.warning("COULD NOT RELEASE REQUEST: " + err.message);
        }
    };

    cdpClient.on('Fetch.requestPaused', async function (reqEvent) {
        if (reqEvent == undefined) {
            return
        }
        const requestId = reqEvent.requestId;
        let responseHeaders = reqEvent.responseHeaders || [];

        // Paused before the response arrived (network error, or a response with
        // no retrievable body such as 401/204/304). Fetch.getResponseBody would
        // reject with "Can only get response body on requests captured after
        // headers received", and because this listener is async that rejection
        // is unhandled and takes down the whole node process - which loses the
        // entire sitespeed run, not just this request.
        if (reqEvent.responseErrorReason != undefined ||
            reqEvent.responseStatusCode == undefined) {
            await releaseRequest(requestId);
            return
        }

        for (const header of headerOptions) {
            // HTTP header names are case-insensitive, and HTTP/2 delivers them in lower case.
            const foundHeaderIndex = responseHeaders.findIndex(
                h => h.name.toLowerCase() === header.name.toLowerCase()
            );
            if (foundHeaderIndex !== -1) {
                context.log.warning("OVERWRITE HTTP HEADER: " + header.name + " = " + header.value);
                responseHeaders[foundHeaderIndex] = header;
            } else {
                context.log.warning("ADDED HTTP HEADER: " + header.name + " = " + header.value);
                responseHeaders.push(header);
            }
        }
        // HACK: for some reason we cant get this to work, so we will use workaround by calling fulfillRequest instead
        // return cdpClient.send('Fetch.continueResponse', {
        //     requestId: requestId,
        //     responseCode: reqEvent.responseStatusCode,
        //     responseHeaders: responseHeaders
        // });

        let bodyResult;
        try {
            bodyResult = await cdpClient.send('Fetch.getResponseBody', {
                requestId: requestId
            });
        } catch (err) {
            // Body was not retrievable after all. Let the request through
            // untouched rather than letting the rejection kill the process.
            context.log.warning("COULD NOT READ RESPONSE BODY: " + err.message);
            await releaseRequest(requestId);
            return
        }

        // Fetch.fulfillRequest expects the body base64 encoded.
        let responseBody = bodyResult.base64Encoded
            ? bodyResult.body
            : Buffer.from(bodyResult.body, 'utf8').toString('base64');

        if (htmlOptions.length > 0) {
            let body = Buffer.from(responseBody, 'base64').toString('utf8');
            for (const html of htmlOptions) {
                context.log.warning("HTML CHANGED: " + html.replace + " = " + html.replaceWith);
                body = body.replace(html.replace, html.replaceWith);
            }
            responseBody = Buffer.from(body, 'utf8').toString('base64');
        }

        try {
            return await cdpClient.send('Fetch.fulfillRequest', {
                requestId: requestId,
                responseCode: reqEvent.responseStatusCode,
                responseHeaders: responseHeaders,
                body: responseBody
            });
        } catch (err) {
            context.log.warning("COULD NOT FULFILL REQUEST: " + err.message);
            await releaseRequest(requestId);
        }
    });
}
