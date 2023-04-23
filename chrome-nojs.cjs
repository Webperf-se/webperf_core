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

        const newServerHeader = { name: 'Content-Security-Policy', value: "script-src 'none';" };
        const foundHeaderIndex = responseHeaders.findIndex(
            h => h.name === 'Content-Security-Policy'
        );
        if (foundHeaderIndex) {
            responseHeaders[foundHeaderIndex] = newServerHeader;
        } else {
            responseHeaders.push(newServerHeader);
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

        return cdpClient.send('Fetch.fulfillRequest', {
            requestId: requestId,
            responseCode: reqEvent.responseStatusCode,
            responseHeaders: responseHeaders,
            body: bodyResult.body
        });
    });
}