/* 
 * USED FOR SITESPEED TEST (TO collect cookies set after a visit)!!!
 */
module.exports = async function (context, commands) {
    try {
        cdpClient = commands.cdp.engineDelegate.getCDPClient()
        // https://chromedevtools.github.io/devtools-protocol/tot/Storage/#method-getCookies
        bodyResult = await cdpClient.send('Storage.getCookies');
        context.log.info('COOKIES:START:', bodyResult, 'COOKIES:END');
    } catch (err) {
        // We probably used firefox... right now we don't have good way of catching cookies
        try {
            // tmp = await commands.js.run('return typeof document !== "undefined"');
            // tmp = await commands.js.run('return typeof document.cookie !== "undefined"');
            // str_cookies = await commands.js.run('return typeof document !== "undefined" && typeof document.cookie !== "undefined" ? [document.cookie] : []');



            context.log.info('COOKIES:START:', {}, 'COOKIES:END');
        } catch (err2) {
            context.log.info('COOKIES:START:', {}, 'COOKIES:END');
        }
    }
}