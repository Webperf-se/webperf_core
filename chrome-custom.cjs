/* 
 * USED FOR SITESPEED TEST (TO test real no javascript gain)!!!
 * Right now sitespeed doesn't support blocking specific content type so this is our workaround
 */
module.exports = async function (context, commands) {
    cdpClient = commands.cdp.engineDelegate.getCDPClient()
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

        if ('webperf' in context.options) {
            for (var i = 1; i <= 9; i++) {
                const key = 'header0X'.replace('X', i);
                if (!(key in context.options.webperf)) {
                    // context.log.warning("NO " + key + " OPTIONS");
                    continue;
                }
                pair = context.options.webperf[key].replaceAll('%20', ' ').split('=');
                const newServerHeader = { name: pair[0].replaceAll('%3D', '='), value: pair[1].replaceAll('%3D', '=') };
                const foundHeaderIndex = responseHeaders.findIndex(
                    h => h.name === pair[0].replaceAll('%3D', '=')
                );
                if (foundHeaderIndex) {
                    context.log.warning("ADDED HTTP HEADER: " + pair[0].replaceAll('%3D', '=') + " = " + pair[1].replaceAll('%3D', '='));
                    responseHeaders[foundHeaderIndex] = newServerHeader;
                } else {
                    context.log.warning("OVERRITE HTTP HEADER: " + pair[0].replaceAll('%3D', '=') + " = " + pair[1].replaceAll('%3D', '='));
                    responseHeaders.push(newServerHeader);
                }
            }
        } else {
            context.log.warning("NO PLUGIN OPTIONS");
        }

        reqEvent.responseHeaders = responseHeaders;
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

        body = ''
        if (bodyResult.base64Encoded) {
            body = atob(bodyResult.body)
        }

        if ('webperf' in context.options) {
            for (var i = 1; i <= 9; i++) {
                const key = 'HTML0X'.replace('X', i);
                if (!(key in context.options.webperf)) {
                    // context.log.warning("NO " + key + " OPTIONS");
                    continue;
                }
                pair = context.options.webperf[key].replaceAll('%20', ' ').split('=');
                context.log.warning("HTML CHANGED: " + pair[0].replaceAll('%3D', '=') + " = " + pair[1].replaceAll('%3D', '='));
                body = body.replace(pair[0].replaceAll('%3D', '='), pair[1].replaceAll('%3D', '='))
            }
        } else {
            context.log.warning("NO PLUGIN OPTIONS");
        }


        try {
            return await cdpClient.send('Fetch.fulfillRequest', {
                requestId: requestId,
                responseCode: reqEvent.responseStatusCode,
                responseHeaders: responseHeaders,
                body: bodyResult.body
            });
        } catch (err) {
            context.log.warning("COULD NOT FULFILL REQUEST: " + err.message);
            await releaseRequest(requestId);
        }
    });
}
