// 서버에서 데이터를 가져오는 비동기 함수
async function getServerData(request) {
    try {
        // fetch: 네트워크 요청을 보내고 응답을 받아오는 웹 API
        // await: 비동기 작업이 완료될 때까지 기다림
        const response = await fetch('./api/serverData', {
            method: 'POST', // HTTP 메서드 (여기서는 POST 요청)
            // JSON.stringify: JavaScript 객체를 JSON 문자열로 변환
            body: JSON.stringify({ request }), // 요청 본문
            headers: { 'Content-Type': 'application/json' } // 요청 헤더
        });

        // 응답이 성공적이지 않으면 오류 발생
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // response.json(): 응답 본문을 JSON으로 파싱
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('Error fetching server data:', error);
        throw error; // 오류를 상위로 전파
    }
}

// AG-Grid의 서버 사이드 데이터소스를 생성하는 함수
function createServerSideDatasource() {
    return {
        // AG-Grid가 새로운 데이터를 요청할 때 호출하는 함수
        getRows: async (params) => {
            try {
                console.log('Request params:', params);
                const result = await getServerData(params.request);
                console.log('Data result:', result);

                // 성공 시 AG-Grid에 데이터 전달
                params.success(result.response);

                // 행 카운터 업데이트
                updateRowCounter(result.counter_info);
            } catch (error) {
                console.error('Failed to fetch server data:', error);
                params.fail(); // AG-Grid에 실패 알림
            }
        }
    };
}

// 행 카운터를 업데이트하는 함수
function updateRowCounter(counterInfo) {
    const counterElement = document.getElementById("row-counter");
    if (counterElement) {
        counterElement.textContent = counterInfo;
    } else {
        console.warn("Row counter element not found");
    }
}

// dash_ag_grid 라이브러리용 전역 함수 객체
window.dashAgGridFunctions = window.dashAgGridFunctions || {};

// 자식 요소 개수를 반환하는 함수
window.dashAgGridFunctions.getChildCount = function (data) {
    return data.childCount;
};

// 서버 사이드 데이터소스 생성 함수를 전역으로 노출
window.createServerSideDatasource = createServerSideDatasource;