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

    cdpClient.on('Fetch.requestPaused', async function (reqEvent) {
        if (reqEvent == undefined) {
            return
        }
        const requestId = reqEvent.requestId;
        let responseHeaders = reqEvent.responseHeaders || [];

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

        bodyResult = await cdpClient.send('Fetch.getResponseBody', {
            requestId: requestId
        });

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


        return cdpClient.send('Fetch.fulfillRequest', {
            requestId: requestId,
            responseCode: reqEvent.responseStatusCode,
            responseHeaders: responseHeaders,
            body: bodyResult.body
        });
    });
}
