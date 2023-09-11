/* 
 * USED FOR SITESPEED TEST (TO collect cookies set after a visit)!!!
 */
module.exports = async function (context, commands) {
    cdpClient = commands.cdp.engineDelegate.getCDPClient()
    // https://chromedevtools.github.io/devtools-protocol/tot/Storage/#method-getCookies
    bodyResult = await cdpClient.send('Storage.getCookies');
    context.log.info('COOKIES:START:', bodyResult, 'COOKIES:END');
}