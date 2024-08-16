async function getServerData(request) {
    const response = await fetch('./api/serverData', {
        method: 'POST',
        body: JSON.stringify({ request }), // Simplified object property
        headers: { 'Content-Type': 'application/json' } // Correct header casing
    });
    const result = await response.json();
    return result

}
 
 
function createServerSideDatasource() {
    return {
        getRows: async (params) => {
            try {
                console.log('Request params:', params);
                const result = await getServerData(params.request);
                console.log('Data result:', result);
                params.success(result.response);
                document.getElementById("row-counter").innerText = result.counter_info;
            } catch (error) {
                console.error('Failed to fetch server data:', error);
                params.fail();
            }
        }
    };
 }
 
 
var dagfuncs = window.dashAgGridFunctions = window.dashAgGridFunctions || {};
dagfuncs.getChildCount = function (data) {
    return data.childCount;
};