using UnityEngine;
using UnityEngine.Networking;
using System.Collections;
using System.Text;
using Newtonsoft.Json;

public class AIController : MonoBehaviour
{
    private string serverUrl = "http://localhost:5000/generate";
    private bool isProcessing = false;
    private bool isMoving = false;
    private Vector2 moveDirection = Vector2.zero;
    private float currentRotationSpeed = 0f;
    private float currentScaleSpeed = 0f;
    private float checkInterval = 1f;
    private string lastCommand = "";

    // 新增跳躍相關變數
    private bool isJumping = false;
    private float jumpForce = 5f;
    private bool isGrounded = true;
    private Rigidbody2D rb;

    [SerializeField]
    private float moveSpeed = 5f;
    [SerializeField]
    private float rotateSpeed = 200f;
    [SerializeField]
    private float scaleSpeed = 2f;
    [SerializeField]
    private LayerMask groundLayer;  // 用於檢測地面的層級

    private void Awake()
    {
        Debug.Log("AIController Awake");
        rb = GetComponent<Rigidbody2D>();
        if (rb == null)
        {
            rb = gameObject.AddComponent<Rigidbody2D>();
            rb.constraints = RigidbodyConstraints2D.FreezeRotation;  // 防止物理旋轉
        }
    }

    private void Start()
    {
        Debug.Log("AIController Start");
        StartCoroutine(CheckForCommands());
    }

    private IEnumerator CheckForCommands()
    {
        Debug.Log("Starting command check coroutine");
        while (true)
        {
            if (!isProcessing)
            {
                Debug.Log("Sending check request to server");
                StartCoroutine(SendAIRequest("check"));
            }
            yield return new WaitForSeconds(checkInterval);
        }
    }

    private void FixedUpdate()
    {
        // 檢查是否在地面上
        isGrounded = Physics2D.Raycast(transform.position, Vector2.down, 0.1f, groundLayer);
    }

    private void Update()
    {
        // 處理持續移動
        if (isMoving)
        {
            transform.Translate(moveDirection * moveSpeed * Time.deltaTime);
        }

        // 處理持續旋轉
        if (currentRotationSpeed != 0)
        {
            transform.Rotate(0, 0, currentRotationSpeed * Time.deltaTime);
        }

        // 處理持續縮放
        if (currentScaleSpeed != 0)
        {
            transform.localScale += Vector3.one * currentScaleSpeed * Time.deltaTime;
        }
    }

    private IEnumerator SendAIRequest(string prompt)
    {
        isProcessing = true;
        Debug.Log($"Starting AI request with prompt: {prompt}");

        var requestData = new { prompt = prompt };
        string jsonData = JsonConvert.SerializeObject(requestData);
        byte[] bodyRaw = Encoding.UTF8.GetBytes(jsonData);

        UnityWebRequest request = new UnityWebRequest(serverUrl, "POST");
        request.uploadHandler = new UploadHandlerRaw(bodyRaw);
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Content-Type", "application/json");

        Debug.Log("Sending request to server...");
        yield return request.SendWebRequest();

        if (request.result == UnityWebRequest.Result.Success)
        {
            Debug.Log($"Request successful. Response: {request.downloadHandler.text}");
            try
            {
                var response = JsonConvert.DeserializeObject<AIResponse>(request.downloadHandler.text);
                
                if (response.success && !string.IsNullOrEmpty(response.response))
                {
                    Debug.Log($"Received command: {response.response}");
                    if (response.response != lastCommand)
                    {
                        lastCommand = response.response;
                        ExecuteAICommand(response.response);
                    }
                }
                else
                {
                    Debug.Log("No valid command received");
                }
            }
            catch (JsonException e)
            {
                Debug.LogError($"JSON parsing error: {e.Message}");
            }
        }
        else
        {
            Debug.LogError($"Request failed: {request.error}");
            Debug.LogError($"Response: {request.downloadHandler.text}");
        }

        isProcessing = false;
    }

    private void ExecuteAICommand(string command)
    {
        Debug.Log($"Executing command: {command}");
        
        // 重置所有動作
        isMoving = false;
        moveDirection = Vector2.zero;
        currentRotationSpeed = 0f;
        currentScaleSpeed = 0f;

        // 設置新的動作
        switch (command)
        {
            case "向左移動":
                isMoving = true;
                moveDirection = Vector2.left;
                break;
            case "向右移動":
                isMoving = true;
                moveDirection = Vector2.right;
                break;
            case "向左旋轉":
                currentRotationSpeed = rotateSpeed;
                break;
            case "向右旋轉":
                currentRotationSpeed = -rotateSpeed;
                break;
            case "放大":
                currentScaleSpeed = scaleSpeed;
                break;
            case "縮小":
                currentScaleSpeed = -scaleSpeed;
                break;
            case "跳躍":
                if (isGrounded)
                {
                    rb.AddForce(Vector2.up * jumpForce, ForceMode2D.Impulse);
                }
                break;
            case "蹲下":
                transform.localScale = new Vector3(1f, 0.5f, 1f);
                break;
            case "伸展":
                transform.localScale = new Vector3(1f, 1f, 1f);
                break;
        }
    }
}

[System.Serializable]
public class AIResponse
{
    public bool success;
    public string response;
    public string error;
}